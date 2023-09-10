from typing import List, Dict

import tiktoken


def get_token_count(model: str, messages: List[Dict[str, str]]) -> int:
    """
    Get token count
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        return 0

    num_tokens = 0
    for message in messages:
        # every message follows <im_start>{role/name}\n{content}<im_end>\n
        num_tokens += 5
        for key, value in message.items():
            if value:
                num_tokens += len(encoding.encode(value))
            if key == "name":  # if there's a name, the role is omitted
                num_tokens += 5  # role is always required and always 1 token
    num_tokens += 5  # every reply is primed with <im_start>assistant
    return num_tokens
