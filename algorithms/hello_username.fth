variable str_length
255 allot

: str_item  (offset -- addr)
    str_length +
;

: input_str
    1                   / initializing i
    begin
        key             / read char from stdin
        over            / copy i and put on tos
        str_item       / resolving address
        !               / putting key in address
                        / now tos is i

        dup             / checking what we wrote
        str_item @
        0 = if
        invert          / first cond - not eof

        over            / copy i and put on tos
        1 +             / update i
        255 <           / second cond - not big str
        or

        dup invert      / if we ending input
        -1 = if
            over        / we need put i as length
            str_length !
    until
;

: print_str
    1                   / initializing i
    begin
        dup
        str_item @      / put symbol code on tos
        emit            / print symbol

        1 +             / update i

        dup
        1 -
        str_length @ <  / end cond - str size
    until
;



."Input your name (max length - 255)"
input_str
."Hello, "
print_str