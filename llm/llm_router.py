from llm import deepseek_client, openai_client


def get_llm_provider(demo_mode=False) -> str:
    if demo_mode is True:
        return "deepseek"
    return "openai"


def is_llm_available(demo_mode=False) -> bool:
    provider = get_llm_provider(demo_mode=demo_mode)
    if provider == "deepseek":
        return deepseek_client.is_available()
    return openai_client.is_available()


def generate_llm_response(messages, context=None, demo_mode=False) -> str | None:
    provider = get_llm_provider(demo_mode=demo_mode)
    if provider == "deepseek":
        return deepseek_client.generate_response(messages, context=context)
    return openai_client.generate_response(messages, context=context)
