from django import template
register = template.Library()

@register.filter
def get_item(mapping, key):
    try:
        return mapping.get(key)
    except Exception:
        return None

@register.filter
def attr(obj, name):
    return getattr(obj, name, None)

@register.filter
def unitfield(code):
    return {
        'SAAD':'saad','SAS':'sas','SAME':'same','SOT':'sot','SOE':'soe','SOED':'soed',
        'BURAUEN':'burauen','CARIGARA':'carigara','DULAG':'dulag','ORMOC':'ormoc','TANAUAN':'tanauan'
    }.get(code, '')
