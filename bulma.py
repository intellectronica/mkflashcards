from fasthtml.common import ft_hx

def kw(kwargs, cls):
    if 'cls' in kwargs:
        kwargs['cls'] = f"{kwargs['cls']} {cls}"
    else:
        kwargs['cls'] = cls
    return kwargs

def Container(*c, **kwargs):
    return ft_hx('div', *c, cls='', **kwargs)

def Button(*c, **kwargs):
    return ft_hx('button', *c, cls='button', **kwargs)

def Textarea(*c, **kwargs):
    return ft_hx('textarea', *c, cls='textarea', **kwargs)

def Input(*c, **kwargs):
    return ft_hx('input', *c, cls='input', **kwargs)

def Label(*c, **kwargs):
    return ft_hx('label', *c, cls='label', **kwargs)

def Card(*c, **kwargs):
    return ft_hx('div', *c, cls='card', **kwargs)

def CardHeader(*c, **kwargs):
    return ft_hx('header', *c, cls='card-header', **kwargs)

def CardHeaderTitle(*c, **kwargs):
    return ft_hx('p', *c, cls='card-header-title', **kwargs)

def CardContent(*c, **kwargs):
    return ft_hx('div', *c, cls='card-content', **kwargs)

def Grid(*c, **kwargs):
    return ft_hx('div', *c, cls='grid', **kwargs)

def Cell(*c, **kwargs):
    return ft_hx('div', *c, **kw(kwargs, cls='cell'))

def Columns(*c, **kwargs):
    return ft_hx('div', *c, **kw(kwargs, cls='columns'))

def Column(*c, **kwargs):
    return ft_hx('div', *c, **kw(kwargs, cls='column'))