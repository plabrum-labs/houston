from enum import StrEnum, auto


class EmbeddingTaskName(StrEnum):
    """Task names for the embeddings service.

    Module-local (not part of the platform's framework `queue.enums.TaskName`): the
    @task registration and the after-commit enqueue both live inside the
    embeddings module, and the registry / enqueue accept any str-valued name
    (cf. form_dsl's `FormNodeActionGroupType`, sequences' demoted `SequenceType`).
    """

    EMBED_ROW = auto()
    SWEEP_EMBEDDINGS = auto()
