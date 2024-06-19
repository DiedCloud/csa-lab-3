variable mod3
variable mod5
variable total
variable number

0 mod3 !
0 mod5 !
0 total !
0 number !


: prob1 ( limit -- sum )
    begin
        mod3 @ 0 =
        mod5 @ 0 =
        or
        if
            number @ total +!   / увеличиваем итоговую сумму на новое число, если оно подходит
        then

        1 mod3 +!
        3 mod3 @ =
        if
            0 mod3 !            / отсчет делимости на 3
        then

        1 mod5 +!
        5 mod5 @ =
        if
            0 mod5 !            / отсчет делимости на 5
        then

        1 number +!             / следующее число

    dup                         / limit должен сохранятся, поэтому дублируем
    number @ = until            / на вершине стека должен остаться limit
    total @
;

1000 prob1 .