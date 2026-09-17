# The DDD Starter Modelling Process

Load this when a team is starting DDD work and does not know where to begin — a greenfield project, a brownfield migration, a programme spanning several teams, a team re-organisation, or an audit of how well the current system fits the business. It is the *before code* half of DDD: the rest of this skill assumes the domain has already been discovered and decomposed, and this is how that happens.

The process comes from the [DDD Crew](https://github.com/ddd-crew/ddd-starter-modelling-process) and is eight steps, meant to be walked in order the first couple of times and then reordered freely. It is a scaffold for beginners, not a standard: real work jumps back and forth between the steps as understanding changes, and the authors say so themselves.

## The eight steps

| # | Step | The question it answers | Start with | Also consider |
|---|------|------------------------|-----------|---------------|
| 1 | **Understand** | What is the business trying to achieve, and for whom? | [Business Model Canvas](https://www.strategyzer.com/canvas/business-model-canvas), [User Story Mapping](https://www.jpattonassociates.com/user-story-mapping/) | [Impact Mapping](https://www.impactmapping.org/), [Product Strategy Canvas](https://melissaperri.com/blog/2016/07/14/what-is-good-product-strategy), [Wardley Mapping](https://learnwardleymapping.com/) |
| 2 | **Discover** | What actually happens in the domain? | [EventStorming](https://www.eventstorming.com/) | [Domain Storytelling](https://domainstorytelling.org/), [Example Mapping](https://cucumber.io/blog/bdd/example-mapping-introduction/), user journey mapping |
| 3 | **Decompose** | Where are the loosely coupled parts? | Carve the event storm into sub-domains | [Business Capability Modelling](https://www.slideshare.net/trondhr/from-capabilities-to-services-modelling-for-businessit-alignment-v2), [Design Heuristics](https://www.dddheuristics.com/), [Independent Service Heuristics](https://github.com/TeamTopologies/Independent-Service-Heuristics) |
| 4 | **Strategize** | Which parts differentiate the business? | [Core Domain Charts](https://github.com/ddd-crew/core-domain-charts) | [Purpose Alignment Model](https://web.archive.org/web/20241202160527/https://www.informit.com/articles/article.aspx?p=1384195&seqNum=2), Wardley Mapping, [Revisiting the Basics of DDD](https://vladikk.com/2018/01/26/revisiting-the-basics-of-ddd/) |
| 5 | **Connect** | How do the parts work together end to end? | [Domain Message Flow Modelling](https://github.com/ddd-crew/domain-message-flow-modelling) | Process-level EventStorming, sequence diagrams, BPMN |
| 6 | **Organise** | Which teams own which parts? | [Context Maps](https://speakerdeck.com/mploed/visualizing-sociotechnical-architectures-with-context-maps) ([pattern summary](https://github.com/ddd-crew/context-mapping)) | [Team Topologies](https://teamtopologies.com/), [Dynamic Reteaming](https://leanpub.com/dynamicreteaming), [Explorers, Villagers & Town Planners](https://medium.com/mappingpractice/how-to-organise-yourself-f36f084a611b) |
| 7 | **Define** | What is each bounded context responsible for? | [Bounded Context Canvas](https://github.com/ddd-crew/bounded-context-canvas) | [C4 system context diagram](https://c4model.com/#SystemContextDiagram), [Quality Storming](https://speakerdeck.com/mploed/quality-storming) |
| 8 | **Code** | What does the model look like in code? | [Aggregate Design Canvas](https://github.com/ddd-crew/aggregate-design-canvas) | Design-level EventStorming, [Event Modeling](https://eventmodeling.org/posts/what-is-event-modeling/), [Model Exploration Whirlpool](https://domainlanguage.com/ddd/whirlpool/), C4 component diagrams, mob programming |

Eduardo da Silva groups the eight into four phases — align and understand (1–2), strategic architecture (3–5), strategy and org design (6), tactical architecture (7–8) — which is a useful way to explain the shape to people who have not seen it.

### What each step is guarding against

- **Understand** — an architecture that is technically fine but pulls against the business goals. Every boundary decision has a business consequence; you cannot judge it without knowing what the business is trying to do.
- **Discover** — the one step you cannot skip. If the whole team does not build a shared picture of the domain, every downstream decision is a guess. Discovery is continuous: teams that succeed with DDD keep running discovery sessions, and a first EventStorming goes much better with someone who has facilitated one before.
- **Decompose** — one big model nobody can hold in their head. Sub-domains cut cognitive load, give teams something to own independently, and expose the coupling that the architecture and the team structure both have to respect.
- **Strategize** — spending the same care everywhere. Time is finite; knowing which sub-domains are core tells you where rigour pays off and where buying or outsourcing is the right answer.
- **Connect** — a clean decomposition that falls apart on the first real use case. Trace concrete end-to-end flows through the proposed parts; hidden coupling shows up here, not on the boundary diagram.
- **Organise** — teams whose boundaries fight the context boundaries. Align the two, size teams for cognitive load and communication overhead, and involve the teams in drawing their own lines rather than handing them down.
- **Define** — committing to a context before the important choices have been made explicit. The canvas forces the conversation about purpose, ubiquitous language, inbound and outbound messages, and business rules while changing your mind is still cheap.
- **Code** — a model in code that nobody but its author recognises. When the people who modelled the problem write the code, the code stays aligned with the domain and is easier to change when the domain changes.

### Who is in the room

Every step wants the people who design, build and test the software plus the people with domain knowledge. Understand, Discover and Organise also want whoever owns product and business strategy; Understand and Discover want real end users, not only their internal stand-ins; Define wants whoever is accountable for the product. Code is the one step that is developers alone — and only because the earlier steps already put the domain experts' knowledge into the developers' heads.

## Reordering it

The order above is the default, not a rule. Reasons to change it that the authors call out:

- **Start with Discover** when the team is more comfortable modelling the domain it knows than talking about business strategy it does not.
- **Start with Connect / Organise** on a brownfield system: map the current landscape first so the constraints are visible before anyone draws a target.
- **Code early** when an MVP has to ship or the domain is so complex that a model in code is the only way to understand it well enough to place boundaries.
- **Loop Discover → Organise several times** before Define, so the system is decomposed more than one way before a bounded context is committed to.
- **Organise before Define** where organisational constraints are real, so you do not design an architecture no team structure can deliver.
- **Blend Define and Code** — writing the code for a context routinely changes its high-level design, and that is fine.

## How it relates to Evans' Whirlpool

Eric Evans' [Model Exploration Whirlpool](https://www.domainlanguage.com/ddd/whirlpool/) covers the modelling loop at the centre of Discover, Define and Code — story, model, code probe, repeat. The Starter Modelling Process adds the strategic and organisational steps around it. Both are guides rather than fixed procedures, and both are iterative; the Whirlpool is still the best account of how to explore a single model.

## How it maps onto this toolkit

- **Discover.** This toolkit's discovery format is event modeling, not EventStorming — the `event-modeling` skill and `/drive` command run the workshop and turn it into slices. The two share the idea of finding pivotal events; the sticky-note grammar differs. Use EventStorming if a facilitator already knows it; otherwise start from `event-modeling`.
- **Decompose, Connect, Define.** `bounded-contexts.md` in this skill covers the context-mapping patterns and how to lay contexts out in code once the Bounded Context Canvas has settled what each one is for. The `ubiquitous-language` skill owns the glossary each canvas produces.
- **Organise.** Team structure is out of scope for the code skills, but the `structure-codebase` skill keeps bounded context as its own structural axis so package boundaries can follow the team boundaries this step decides.
- **Code.** The Aggregate Design Canvas feeds straight into `aggregate-design.md` (sizing, invariants, one aggregate per transaction). Hexagonal architecture is one of the process's Code-step options; in this toolkit it is the separate `hexagonal-architecture` skill, and DDD does not require it.

## Attribution

Adapted from the [DDD Starter Modelling Process](https://github.com/ddd-crew/ddd-starter-modelling-process) by the DDD Crew and contributors (Ciaran McNulty, Eduardo da Silva, Gien Verschatse, James Morcom, Maxime Sanglan-Charlier, Javiera Javichi and others), pinned at revision [`1eff6def`](https://github.com/ddd-crew/ddd-starter-modelling-process/blob/1eff6def298d4212ceaf297e00970b0505347b5a/README.md). The upstream work is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); this file is a condensed adaptation with the toolkit mapping added, and no upstream endorsement is implied. The original includes the process diagram, per-step illustrations, translations and case studies that are not reproduced here.
