def karakterTemizle(kelime):

    karakterler = {
    'ü':'u',
    'ö':'o',
    'ş':'s',
    'ğ':'g',
    'ı':'i',
    'ç':'c',
    'Ü':'u',
    'Ö':'o',
    'Ç':'c',
    'Ğ':'g',
    'I':'i',
    'İ':'i'
    }
    new_kelime = ''
    for k in kelime:
        if k in karakterler.keys():
            k = karakterler[k]
        new_kelime += k
    return new_kelime
