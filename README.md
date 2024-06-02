# Лабораторная работа №3 "Эксперимент"

## Вариант
```
forth | stack | harv | mc -> hw | tick -> instr | struct | stream | mem | pstr | prob1 | cache
```
 - Фролов Кирилл Дмитриевич P3206
 - Базовый вариант

### Расшифровка
   - Низкоуровневый язык ***Forth*** (с обратной польской нотацией и поддержкой процедур)
   - ***Стековая*** архитектура процессора
   - ***Гарвардская архитектура*** (раздельная память для команд и данных)
   - Управление посредствам ***микрокода***
   - Симуляция с точностью до ***тактов***
   - Машинный код хранится как ***высокоуровневая структура***
   - ***Потоковый*** ввод-вывод (без прерываний)
   - Устройства ввода-вывода адресуются через ***память*** (без особых инструкций для ввода-вывода)
   - ***Pascal strings*** (длина строки + содержимое)
   - Project euler problem 1 (алгоритм для реализации на языке forth)
   - ~~Кэширование~~ (не реализовано)

## Оглавление
1. [Вариант](#вариант)
    - [Расшифровка](#расшифровка)
2. [Язык программирования](#язык-программирования)
   - [Синтаксис](#синтаксис)
   - [Семантика](#семантика)
   - [Литералы](#литералы)
   - [Типы аргументов](#типы-аргументов)
3. [Организация памяти](#организация-памяти)
4. [Система команд](#система-команд)
5. [Транслятор](#транслятор)
6. [Модель процессора](#модель-процессора)
7. [Тестирование](#тестирование)
8. [Общая статистика](#общая-статистика)

## Язык программирования

Реализуется подмножество языка Forth для программ из задания. [Сами программы](algorithms). 

### Синтаксис

```ebnf
<program> ::= <line>*

<line> ::= <instr> <comment>? "\n"
       | <comment>? "\n"

<instr> ::= <op> | <procedure_call>

<op> ::= <control_op>
      | <op-1-0>
      | <op-2-0>
      | <op-0-1>
      | <op-1-1>
      | <op-2-1>

<control_op> ::= "then"
      | "begin"
      | ":"
      | ";"
      | "("
      | ")"
      | "variable"
      | "allot"
      | "\""

<op-1-0> ::= "if"
      | "until"
      | "emit"
      | "."
      
<op-2-0> ::= "+!"
      | "!"

<op-0-1> ::= "dup"
      | "over"
      | "key"

<op-1-1> ::= "@"

<op-2-1> ::= "+"
      | "-"
      | "="
      | "<"
      | ">"
      | "or"
      | "and"
      
<procedure_call> ::= <procedure_name>
<procedure_name> ::= <letter>*

<lowercase_letter> ::= [a-z]
<uppercase_letter> ::= [A-Z]
<letter> ::= <lowercase_letter> | <uppercase_letter>

<positive_integer> ::= [0-9]+
<integer> ::= "-"? <positive_integer>

<any_letter> ::= <lowercase_letter>
      | <uppercase_letter>
      | <integer>
      | " "

<comment> ::= " "* "/" " "* <any_letter>*
```

### Семантика
   - Код выполняется последовательно, одна инструкция за одной.
   - Список встроенных [инструкций]().
   - Также же можно определять собственные процедуры:
     - Для этого нужно использовать ":" для начала определения процедуры;
     - Можно написать не влияющую на исполнение программы аннотацию сигнатуры: "(операнды -- возвращаемое значение)"; 
     - Написать название процедуры как непрерывную последовательность символов;
     - Написать последовательность инструкций литералов и вызовов процедур для определения тела процедуры;
     - Использовать ";" для завершения определения процедуры.
   - Процедуры используют встроенные инструкции или другие процедуры, поэтому также взаимодействуют со стеком.
   - Использовать одну процедуру можно неограниченное количество раз.

Пример определения процедуры:
```forth
:  my_procedure_name (op1, op2 -- result)
   other_procedure
   1
   +
;
```
`my_procedure_name` увеличит значение, полученное из `other_procedure`. Результат `result` останется на вершине стека, а `op1, op2`, вероятно, будут задействованы в `my_procedure_name`. 

### Литералы
   1. Любое целое число воспринимается как команда положить это число на вершину стека.
   2. Строка (область ограниченная `"`) воспринимается как инициализация строки в памяти. Ее можно вывести с помощью `.`. Пример этого в программе [hello world](algorithms/hello_world.fth).  

## Организация памяти

* Машинное слово – не определено. Инструкции хранятся в высокоуровневой структуре данных.
* Размер операнда – не определен. Интерпретируется как знаковое целое число.
* Адресация – прямая, абсолютная, доступ к словам. Адрес берется с вершины стека. Косвенную адресацию можно реализовать программно.
* Программист не взаимодействует с адресами памяти данных на прямую.
  Транслятор сам решает, в каком месте выделить память под программу и под данные программы.
* Программа и данные хранятся в раздельной памяти согласно Гарвардской архитектуре.
  Программа состоит из набора инструкций, последняя инструкция – `HALT`.
  Процедуры размещаются в той же памяти, они обязаны завершаться при помощи инструкции `RET`.
* Литералы - знаковые числа. Константы отсутствуют.

Организация стека:

* Стек реализован в виде высокоуровневой структуры данных (`array`)
* В data-path стек - это 2 регистра:
  * `TOS` - вершина стека
  * `TOS-1` - следующий за вершиной элемент (нужен для инструкций с двумя операндами или для инструкции over)
* Ячейка стека может уместить один операнд одной ячейки памяти.

## Система команд

Особенности процессора:

* Машинное слово – не определено.
* Тип данных - знаковые числа, или логические значения, или символы ascii (в рамках модели на python эти типы так и хранятся)
* Доступ к памяти осуществляется по адресу из вершины стека.
* Обработка данных осуществляется в стеке. Данные попадают в стек из:
  * Памяти. ___Устройства ввода-вывода привязаны к ячейкам памяти.___
  * С помощью инструкции LIT.
  * АЛУ кладет результат вычислений на вершину стека.
* Поток управления:
  * Значение `PC` инкриминируется после исполнения каждой инструкции;
  * Условный (`JZ`) и безусловный (`JUMP`) переходы;
  * Микропрограммное управление - каждый такт выполняется одна микрокоманда и посредствам счетчика микрокоманд решается, какая станет следующей. 

Набор инструкций:

* `NOP` – нет операции.
* `LIT <literal>` – положить число на вершину стека.
* `LOAD { data_address }` – загрузить из памяти значение по адресу с вершины стека.
* `STORE { data_address, element }` – положить значение в память по указанному адресу.
* `DUP { element }` – дублировать элемент, лежащий на вершине стека.
* `OVER { e1 } [ e2 ]` – дублировать элемент, лежащий на 1 глубже вершины. Если в стеке только 1 элемент – поведение не определено.
* `ADD { e1, e2 }` – положить на стек результат операции сложения e2 + e1.
* `SUB { e1, e2 }` – положить на стек результат -e1.
* `AND { e1, e2 }` – положить на стек результат операции логического И.
* `OR { e1, e2 }` – положить на стек результат операции логического ИЛИ.
* `INV {e1}` - инвертировать логическое значение на вершине стека.
* `ISNEG {e1}` - положить на вершину значение флага Negative.
* `JZ { element, program_address }` – если элемент равен 0, начать исполнять инструкции по указанному адресу. Условный переход.
* `JUMP { program_address }` – безусловный переход по указанному адресу.
* `CALL { program_address }` – начать исполнение процедуры по указанному адресу.
* `RET` – вернуться из процедуры в основную программу, на следующий адрес.
* `HALT` – остановка тактового генератора.

Взятие операнда со стека - `{ op }`. \
Указание операнда в инструкции - `< op >`. \
Если операции требуется дополнительный операнд, но он не используется, он обозначен `[ в квадратных скобках ]`.

Если команда задействует операнд, то она снимает его со стека.
___Кроме команд `DUP` и `OVER`.___ \
Они читают, но не перемещают stack pointer после чтения и кладут дублируемое значение наверх.

Согласно [варианту](#вариант) машинный код хранится в высокоуровневой структуре. 
Это реализуется списком словарей (в python соответствуют json объектам).
Один элемент списка — это одна инструкция.
Индекс инструкции в списке – адрес этой инструкции в памяти команд.

Пример машинного слова:
```json
{
  "opcode": "LIT",
  "operand": 2
}
```

Где:
* `opcode` – строка с кодом операции
* `operand` – аргумент команды (обязателен для инструкций с операндом)

Система команд реализована в модуле [isa](/isa.py).

## Транслятор
## Модель процессора
## Тестирование
## Общая статистика