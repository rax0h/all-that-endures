"""Read-only personhood contracts; no World state, RNG or inferred mental traits."""
from dataclasses import dataclass
from enum import Enum


class EpistemicLevel(str, Enum):
    FACT = 'objective_record'
    OBSERVATION = 'observation'
    BELIEF = 'memory_or_belief'
    PUBLIC_CLAIM = 'public_claim'
    INTERPRETATION = 'authored_interpretation'


@dataclass(frozen=True)
class EntityIdentity:
    kind: str
    id: int | str


@dataclass(frozen=True)
class Embodiment:
    model: str | None = None
    species: str | None = None
    origin_model: str | None = None
    mortality_model: str | None = None
    dependencies: tuple[EntityIdentity, ...] = ()


@dataclass(frozen=True)
class Capabilities:
    # None means unmodeled, never average or incapable. No aggregate score.
    reasoning: float | None = None
    learning: float | None = None
    working_memory: float | None = None
    long_term_memory: float | None = None
    verbal: float | None = None
    spatial: float | None = None
    numerical: float | None = None
    practical: float | None = None
    social_perception: float | None = None
    creativity: float | None = None
    attention: float | None = None


@dataclass(frozen=True)
class Dispositions:
    temperament: float | None = None
    attachment: float | None = None
    curiosity: float | None = None
    inhibition: float | None = None


@dataclass(frozen=True)
class EmotionalState:
    grief: float | None = None
    fear: float | None = None


@dataclass(frozen=True)
class SubjectiveState:
    # No observation-to-memory conversion exists yet. Empty != omniscient.
    observations: tuple[int, ...] = ()
    memories: tuple[int, ...] = ()
    beliefs: tuple[tuple[int, float], ...] = ()
    self_claims: tuple[int, ...] = ()
    coverage: str = 'legacy claim confidence only; memory and self-concept unmodeled'


@dataclass(frozen=True)
class PersonhoodView:
    identity: EntityIdentity
    embodiment: Embodiment
    capabilities: Capabilities = Capabilities()
    dispositions: Dispositions = Dispositions()
    emotions: EmotionalState = EmotionalState()
    subjective: SubjectiveState = SubjectiveState()


def from_person(person, beliefs=()):
    """Adapter only; caller supplies this individual's recorded claim confidence.

    Other entity types can construct PersonhoodView without a biological Person.
    This does not assert that every threat, summon or animal is sapient.
    """
    return PersonhoodView(
        EntityIdentity('person', person.id),
        Embodiment('existing species/rank biology', person.species),
        dispositions=Dispositions(person.temperament, person.attachment,
                                  person.curiosity, person.inhibition),
        emotions=EmotionalState(person.grief, person.fear),
        subjective=SubjectiveState(beliefs=tuple(sorted(beliefs))),
    )
