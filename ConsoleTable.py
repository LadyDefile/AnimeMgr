
# ConsoleTable.py
# Author: LadyDefile
# Description: This is a python module written by LadyDefile
# as a lightweight and easy to use tool for printing tables to 
# the terminal window for the organization of data.

JUSTIFY_LEFT = -1
JUSTIFY_RIGHT = 1
JUSTIFY_CENTER = 0

class ConsoleTableColumn:
    rows=[]
    def __init__(self, header:str = '', width:int = 0, justify:int = -1, padding: tuple=(1,1)) -> None:
        self.header = header
        self.width = width
        self.justify = justify
        self.padding = padding if len(padding) == 2 else (1,1)

    def append(self, data):
        self.rows.append(data)
    
class ConsoleTable:
    print_headers=True
    columns = []
    rows = []

    def add_column(self, title: str ='', justification: int = -1, column_width: int =0):
        tc = ConsoleTableColumn()
        tc.header = title
        tc.justify = justification
        tc.width = column_width
        self.add_column(tc)

    def add_column(self, col: ConsoleTableColumn):
        self.columns.append(col)

    def add_row(self, row: tuple, color: str = '\033[0m') -> None:
        self.rows.append((row, color))

    def get_width(self):
        w = 0
        for c in self.columns:
            w += c.width + 1
        return w
    
    def _fit_str(self, s:str, length: int, justify: int = -1, trunc_str: str='...', padding_left=1, padding_right=1) -> str:
        s = str(s)
        length -= padding_left + padding_right
        spaces = length - len(s)
        if spaces > 0:
            if justify == 1:
                sp = ' ' * (spaces + padding_left)
                return sp+s

            elif justify == 0:
                sp = ' ' * (padding_left + int(spaces / 2 + spaces % 2))
                ssp = ' ' * (padding_right + int(spaces / 2))

                return sp+s+ssp
            else:
                sp = ' ' * padding_left
                ssp = ' ' * padding_right
                ssp += ' ' * spaces
                return sp+s+ssp

        elif spaces < 0:
            sp = ' ' * padding_left
            ssp = ' ' * padding_right
            return sp+s[0:length-len(trunc_str)]+trunc_str+ssp
        else:
            return s
    
    def print(self):
        separator = False
        if self.print_headers:
            row_list = []
            for i in range(0, len(self.columns)):
                col = self.columns[i]
                line = self._fit_str(col.header, col.width, col.justify, padding_left=col.padding[0], padding_right=col.padding[1])
                
                row_list.append(line)

            print('|'.join(row_list))
            separator = True

        for row_data in self.rows:
            if separator:
                print('-'*self.get_width())
            else:
                separator = True

            row = row_data[0]
            row_color = row_data[1]

            row_list = []
            for i in range(0, len(self.columns)):
                line = ''
                col = self.columns[i]
                if i < len(row):
                    line = f'{row_color}{self._fit_str(row[i], length=col.width, justify=col.justify, padding_left=col.padding[0], padding_right=col.padding[1])}\033[0m'
                else:
                    line = f'{row_color}{self._fit_str("", length=col.width, justify=col.justify, padding_left=col.padding[0], padding_right=col.padding[1])}\033[0m'
                row_list.append(line)

            print('|'.join(row_list))

    def flush(self):
        self.rows = []
                    

if __name__ == "__main__":
    table = ConsoleTable()
    table.add_column(ConsoleTableColumn('Animal', 20, JUSTIFY_RIGHT, (1,1)))
    table.add_column(ConsoleTableColumn('Species', 20, padding=(1,1)))
    table.add_column(ConsoleTableColumn('Value', 20, JUSTIFY_CENTER, (1,1)))
    table.add_column(ConsoleTableColumn('Frequency', 20))

    table.add_row(('Fish', 'Tuna', 'Omega 3', 'Common'), '\033[32m')
    table.add_row(('Fish', 'Salmon', 'Omega 3', 'Rare'), '\033[31m')
    table.add_row(('Fish', 'Mermaid', 'Sex Toy Only', 'Rare'), '\033[31m')
    table.print()
