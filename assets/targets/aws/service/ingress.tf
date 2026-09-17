# How traffic reaches each service, and what blue/green needs from that path.
#
# Every service has its own load balancer, two target groups and one listener rule. Two target groups
# because a blue/green deploy is a swap: the new revision's tasks register with the group that has no
# traffic, pass their health checks there, and only then does ECS point the listener rule at that group and
# leave the old tasks up, drained, for the bake time — so a rollback in that window is the rule pointing back,
# not a redeploy. One load balancer per service rather than one for all, because without a domain of its
# own this stack has no host names to route by, and a path prefix would have to be something the services
# knew about; a domain and host-based rules on one balancer are the change that collapses them later.
#
# The load balancer speaks plain HTTP: a certificate needs a domain. CloudFront in front of it is what gives
# every service the HTTPS address `urls` reports and `make smoke` asks — on CloudFront's own domain, inside
# its free tier at this scale, with caching off and every header but Host passed through.

resource "aws_security_group" "ingress" {
  for_each = var.services

  name        = "${local.prefix}-${each.key}-ingress"
  description = "The ${each.key} load balancer: HTTP from anywhere, the service port to the tasks"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port        = 80
    to_port          = 80
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  egress {
    from_port   = each.value.port
    to_port     = each.value.port
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.default.cidr_block]
  }
}

resource "aws_lb" "service" {
  for_each = var.services

  # A load balancer's name is 32 characters at most.
  name               = trimsuffix(substr("${local.prefix}-${each.key}", 0, 32), "-")
  load_balancer_type = "application"
  security_groups    = [aws_security_group.ingress[each.key].id]
  subnets            = data.aws_subnets.default.ids
}

# Which of the two is blue is whichever the listener rule points at today; ECS keeps that straight and the
# names here are only where each started. `name_prefix` because a group's name is 32 characters at most too.
resource "aws_lb_target_group" "blue" {
  for_each = var.services

  name_prefix          = "blue-"
  port                 = each.value.port
  protocol             = "HTTP"
  target_type          = "ip"
  vpc_id               = data.aws_vpc.default.id
  deregistration_delay = 30

  health_check {
    path                = each.value.health_path
    matcher             = "200"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = { Service = each.key }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_lb_target_group" "green" {
  for_each = var.services

  name_prefix          = "green-"
  port                 = each.value.port
  protocol             = "HTTP"
  target_type          = "ip"
  vpc_id               = data.aws_vpc.default.id
  deregistration_delay = 30

  health_check {
    path                = each.value.health_path
    matcher             = "200"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = { Service = each.key }

  lifecycle {
    create_before_destroy = true
  }
}

# The listener answers nothing itself; the rule below is what forwards, because ECS needs a rule it can
# repoint, and a listener's default action is not one.
resource "aws_lb_listener" "http" {
  for_each = var.services

  load_balancer_arn = aws_lb.service[each.key].arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "fixed-response"

    fixed_response {
      content_type = "text/plain"
      status_code  = "404"
    }
  }
}

resource "aws_lb_listener_rule" "production" {
  for_each = var.services

  listener_arn = aws_lb_listener.http[each.key].arn
  priority     = 1

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.blue[each.key].arn
  }

  condition {
    path_pattern {
      values = ["/*"]
    }
  }

  # ECS repoints this rule at every deploy; an apply that put it back would undo the release.
  lifecycle {
    ignore_changes = [action]
  }
}

data "aws_cloudfront_cache_policy" "disabled" {
  name = "Managed-CachingDisabled"
}

data "aws_cloudfront_origin_request_policy" "all_viewer_except_host" {
  name = "Managed-AllViewerExceptHostHeader"
}

resource "aws_cloudfront_distribution" "service" {
  for_each = var.services

  enabled         = true
  is_ipv6_enabled = true
  comment         = "${local.prefix}-${each.key}"
  price_class     = "PriceClass_100"

  origin {
    domain_name = aws_lb.service[each.key].dns_name
    origin_id   = "service"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id         = "service"
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods           = ["GET", "HEAD"]
    compress                 = true
    cache_policy_id          = data.aws_cloudfront_cache_policy.disabled.id
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.all_viewer_except_host.id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

locals {
  # The load balancer's own name, for anything inside AWS that fronts the service itself (the site's
  # distribution routes `/api/*` here), and the HTTPS address for everything else.
  service_origins = { for name, balancer in aws_lb.service : name => balancer.dns_name }
  service_urls    = { for name, distribution in aws_cloudfront_distribution.service : name => "https://${distribution.domain_name}" }
}
