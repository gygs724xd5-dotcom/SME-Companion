from llm import deepseek_client, openai_client


def get_llm_provider(demo_mode=False) -> str:
    if demo_mode is True:
        return "deepseek"
    return "openai"


def is_llm_available(demo_mode=False) -> bool:
    provider = get_llm_provider(demo_mode=demo_mode)
    print(f"LLM provider selected: {provider}")
    print(f"LLM demo_mode: {bool(demo_mode)}")
    if provider == "deepseek":
        available = deepseek_client.is_available()
    else:
        available = openai_client.is_available()

    print(f"LLM api key exists: {available}")
    return available


def provider_has_api_key(demo_mode=False) -> bool:
    provider = get_llm_provider(demo_mode=demo_mode)
    if provider == "deepseek":
        return deepseek_client.has_api_key()
    return openai_client.is_available()


def generate_llm_response(messages, context=None, demo_mode=False) -> str | None:
    provider = get_llm_provider(demo_mode=demo_mode)
    print(f"LLM provider selected: {provider}")
    print(f"LLM demo_mode: {bool(demo_mode)}")
    print(f"LLM api key exists: {provider_has_api_key(demo_mode=demo_mode)}")
    if provider == "deepseek":
        response = deepseek_client.generate_response(messages, context=context)
    else:
        response = openai_client.generate_response(messages, context=context)

    print(f"LLM provider response: {'success' if response else 'fail'}")
    return response
