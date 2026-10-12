# The browser app: a private S3 bucket behind one CloudFront distribution with two origins — the bucket for
# everything, and the service its `/api` goes to for `/api/*`. Same origin from the browser's point of view,
# which is what lets the bundle call `/api/...` relatively in every environment and never pay a CORS
# preflight, exactly as the Vite dev server arranges locally.
#
# scripts/deploy.py uploads the bundle: hashed assets first, as immutable; `index.html` last, with
# `Cache-Control: no-store`, so it is the release pointer — and a copy under `releases/<commit>/` is what a
# rollback puts back.
resource "aws_s3_bucket" "web" {
  bucket = "${local.prefix}-web-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_public_access_block" "web" {
  bucket                  = aws_s3_bucket.web.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_cloudfront_origin_access_control" "web" {
  name                              = "${local.prefix}-web"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

data "aws_cloudfront_cache_policy" "optimized" {
  name = "Managed-CachingOptimized"
}

locals {
  # The service's own load balancer, not its CloudFront address: one hop, and HTTPS is this distribution's.
  api_origin = local.service_origins[var.web.api]
}

# A single-page app owns its routes: a path the bundle routes itself is the app's to render, not an object the
# bucket is missing. The rewrite is a viewer-request function on the site's behaviour alone, and not
# `custom_error_response`, because that block is the whole distribution's — CloudFront has no per-behaviour
# error configuration — so it would turn the service's `404 {"error":"notFound"}` on `/api/*` into this page
# with a `200` beside it, and a bundle asking `/api/...` would parse HTML as its answer. A path whose last
# segment has no `.` is a route; anything else is a file, and a file the bucket does not have is an error the
# browser should see.
resource "aws_cloudfront_function" "spa" {
  name    = "${local.prefix}-spa"
  runtime = "cloudfront-js-2.0"
  comment = "${local.prefix}: serve index.html for the app's own routes"
  publish = true

  code = <<-JS
    function handler(event) {
      var request = event.request;
      var last = request.uri.substring(request.uri.lastIndexOf('/') + 1);
      if (last.indexOf('.') === -1) {
        request.uri = '/index.html';
      }
      return request;
    }
  JS
}

resource "aws_cloudfront_distribution" "web" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = local.prefix
  default_root_object = "index.html"
  price_class         = "PriceClass_100"

  origin {
    domain_name              = aws_s3_bucket.web.bucket_regional_domain_name
    origin_id                = "web"
    origin_access_control_id = aws_cloudfront_origin_access_control.web.id
  }

  origin {
    domain_name = local.api_origin
    origin_id   = "api"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = "web"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    cache_policy_id        = data.aws_cloudfront_cache_policy.optimized.id

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.spa.arn
    }
  }

  ordered_cache_behavior {
    path_pattern             = "/api/*"
    target_origin_id         = "api"
    viewer_protocol_policy   = "https-only"
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

data "aws_iam_policy_document" "web" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.web.arn}/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.web.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "web" {
  bucket = aws_s3_bucket.web.id
  policy = data.aws_iam_policy_document.web.json
}

locals {
  public_url = "https://${aws_cloudfront_distribution.web.domain_name}"
}

output "web_bucket" {
  description = "Where scripts/deploy.py uploads the bundle."
  value       = aws_s3_bucket.web.bucket
}
