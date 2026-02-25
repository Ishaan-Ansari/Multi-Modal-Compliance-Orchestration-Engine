from enum import Enum

DEFAULT_OPENAI_SEED_VALUE = 10

class GPT_Model(Enum):
    GPT_40_MINI = "gpt-4o-mini"
    GPT_03_MINI = "o3-mini"
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    GPT_40 = "gpt-4o"
    GPT_4_1 = "gpt-4.1"
    GPT_4_1_NANO = "gpt-4.1-nano"

    @classmethod
    def values(cls):
        return [i.value for i in cls]
