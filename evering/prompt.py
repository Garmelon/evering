from typing import Optional

__all__ = ["prompt_choice", "prompt_yes_no"]


def prompt_choice(question: str, options: str) -> str:
    default_option = None
    for char in options:
        if char.isupper():
            default_option = char
            break

    option_string = "/".join(options)

    while True:
        result = input(f"{question} [{option_string}] ").lower()
        if not result and default_option:
            return default_option
        # The set() makes it so that we're only testing individual
        # characters, not substrings.
        elif result in set(options.lower()):
            return result
        else:
            print(f"Invalid answer, please choose one of [{option_string}].")


def prompt_yes_no(question: str, default_answer: Optional[bool]) -> bool:
    if default_answer is None:
        options = "yn"
    elif default_answer:
        options = "Yn"
    else:
        options = "yN"

    result = prompt_choice(question, options)
    return result.lower() == "y"
