from __future__ import annotations

"""Small Korean particle helpers for dynamic user-visible names and titles."""


def has_final_consonant(text: str) -> bool:
    for char in reversed(str(text).strip()):
        code = ord(char)
        if 0xAC00 <= code <= 0xD7A3:
            return (code - 0xAC00) % 28 != 0
        if char.isalnum():
            return False
    return False


def with_particle(text: str, consonant: str, vowel: str) -> str:
    clean = str(text).strip()
    return clean + (consonant if has_final_consonant(clean) else vowel)


def quoted_object(text: str) -> str:
    clean = str(text).strip()
    return f'“{clean}”' + ('을' if has_final_consonant(clean) else '를')


def named_subject(name: str) -> str:
    """Use the friendly name convention requested for monster names: 콩이가 / 모모가."""
    clean = str(name).strip()
    return clean + ('이가' if has_final_consonant(clean) else '가')
