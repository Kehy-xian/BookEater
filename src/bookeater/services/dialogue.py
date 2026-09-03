from __future__ import annotations

"""Diegetic dialogue chosen from the monster's established visible lineage.

No hidden trait names, scores or thresholds are exposed.  Dialogue becomes slightly more assured
as more meaningful records accumulate, while the broad voice follows the permanent A/B/C route.
"""

import random

from .memory import broad_route


_EARLY = (
    '오늘은 어떤 문장을 먹게 될까?',
    '책 냄새가 나는 것 같아.',
    '조금 더 읽으면 나도 조금 더 알게 될까?',
)

_ROUTE_LINES = {
    'starter': (
        '아직은 뭐가 제일 맛있는 문장인지 모르겠어.',
        '천천히 먹어 볼래. 서두르지 않아도 돼.',
    ),
    'route_a': (
        '방금 떠오른 질문이 있는데… 조금 더 생각해 볼래?',
        '한 문장을 오래 들여다보면 전에 안 보이던 게 보여.',
        '답보다 질문이 오래 남는 날도 괜찮은 것 같아.',
    ),
    'route_b': (
        '이상하지? 어떤 장면은 다 읽고도 마음에 계속 남아.',
        '오늘 먹은 문장에는 온도가 조금 있었어.',
        '말투 하나만 달라져도 장면의 느낌이 완전히 바뀌더라.',
    ),
    'route_c': (
        '아까 문장이랑 예전에 먹은 문장이 묘하게 이어져.',
        '서로 다른 이야기를 붙여 보면 뜻밖의 길이 생겨.',
        '한 책의 끝이 다른 책의 시작처럼 느껴질 때가 있어.',
    ),
}

_MATURE = {
    'starter': ('아직 정해지지 않은 것도 하나의 모습일지 몰라.',),
    'route_a': ('예전보다 질문을 오래 품는 법을 조금 알 것 같아.',),
    'route_b': ('예전보다 네가 오래 기억하는 장면을 조금 알아보겠어.',),
    'route_c': ('기억들이 서로 연결되는 순간을 이제 제법 알아보겠어.',),
}

_BOND_LINES = {
    'low': ('아직은 조금 낯설지만, 곁에 있어도 괜찮아.',),
    'mid': ('네가 오면 오늘은 무슨 책 이야기일지 궁금해.',),
    'high': ('왔구나! 오늘도 네 문장을 기다리고 있었어.', '우리 제법 서로를 잘 알게 된 것 같아.'),
}


def choose_ambient_line(
    form_id: str,
    entry_count: int,
    *,
    bond: int = 0,
    rng: random.Random | None = None,
) -> str:
    rng = rng or random.Random()
    route = broad_route(form_id)
    count = max(0, int(entry_count))
    pool = list(_ROUTE_LINES.get(route, _ROUTE_LINES['starter']))
    if count < 5:
        pool.extend(_EARLY)
    if count >= 40:
        pool.extend(_MATURE.get(route, ()))
    bond = max(0, min(100, int(bond)))
    bond_group = 'high' if bond >= 65 else ('mid' if bond >= 25 else 'low')
    pool.extend(_BOND_LINES[bond_group])
    return rng.choice(pool)


def greeting_line(form_id: str, bond: int, *, rng: random.Random | None = None) -> str:
    """A relationship-aware launch greeting whose broad voice still follows lineage."""
    rng = rng or random.Random()
    bond = max(0, min(100, int(bond)))
    if bond >= 65:
        prefix = rng.choice(('다시 만나서 반가워!', '기다리고 있었어!'))
    elif bond >= 25:
        prefix = rng.choice(('왔구나.', '오늘도 만났네.'))
    else:
        prefix = rng.choice(('안녕… 천천히 친해져 보자.', '처음엔 조금 조용할지도 몰라.'))
    return f'{prefix} {choose_ambient_line(form_id, 0, bond=bond, rng=rng)}'


def after_feed_line(form_id: str, *, rng: random.Random | None = None) -> str:
    rng = rng or random.Random()
    route = broad_route(form_id)
    pools = {
        'starter': ('잘 먹었어. 이건 조금 더 품고 있어 볼게.', '새 문장 하나가 들어왔어.'),
        'route_a': ('음… 이건 생각할 거리가 꽤 있네.', '이 문장은 조금 오래 씹어 봐야겠어.'),
        'route_b': ('이 문장은 느낌이 오래 남을 것 같아.', '방금 기록은 마음 한쪽에 잘 넣어둘게.'),
        'route_c': ('이거, 예전에 먹은 것과 어디선가 이어질 것 같아.', '새 연결 하나가 생길지도 모르겠어.'),
    }
    return rng.choice(pools.get(route, pools['starter']))
