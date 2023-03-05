import re


def remove_nbsp(func):
    def inner(*args, **kwargs):
        return str.replace(func(*args, **kwargs), '&nbsp;', '')
    return inner


def remove_br_tag(func):
    def inner(*args, **kwargs):
        return str.replace(func(*args, **kwargs), '<br />', '\n')
    return inner


def remove_p_tag(func):
    def inner(*args, **kwargs):
        return str.replace(func(*args, **kwargs),'<p>', '').replace('</p>', '')
    return inner


def wallet_valid(wallet_id: str):
    regex = re.compile('^0x[a-fA-F0-9]{40}$')
    return re.match(regex, wallet_id) is not None


def discord_valid(discord_username: str):
    regex = re.compile('^.{3,32}#[0-9]{4}$')
    return re.match(regex, discord_username) is not None


def amount_valid(amount: str):
    re_float = re.compile(r"(^\d+\.\d+$|^\.\d+$)")
    re_int = re.compile(r"(^[1-9]+\d*$|^0$)")
    return re.match(re_float, amount) is not None or re.match(re_int, amount) is not None


@remove_br_tag
@remove_p_tag
@remove_nbsp
def remove_tags(description: str):
    return description
