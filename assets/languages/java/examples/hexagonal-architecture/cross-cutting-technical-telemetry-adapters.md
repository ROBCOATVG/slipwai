```java
// Driving adapter: log the request and response cycle, which is the transport's own business.
@POST
public Response pledge(@Valid PledgeBody body) {
    PledgeResult result = pledging.pledgeToOccasion(body.toCommand());
    if (result instanceof PledgeResult.Refused refused) {
        LOG.warnf("Pledge refused: %s for occasion %s", refused.reason(), body.occasionId());
    }
    return toResponse(result);
}

// Driven adapter: log the infrastructure interaction, at the level the infrastructure deserves.
final class JdbcOccasionRepository implements OccasionRepository {

    private static final Logger LOG = Logger.getLogger(JdbcOccasionRepository.class);

    @Override
    public void save(Occasion occasion) {
        // ... the write ...
        LOG.debugf("Occasion saved: %s", occasion.id());
    }
}

// Note what neither of these is: a log statement inside a use case or a domain function. Those would put
// a severity decision — a technical judgement about operations — in the middle of a business rule.
```
