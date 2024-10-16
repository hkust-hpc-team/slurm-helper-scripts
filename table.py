import shutil
import math


class Table:
    def __init__(self, title=None):
        self.title = title
        self.columns = []
        self.rows = []
        self.subtables = {}  # {(row_idx, col_idx): subtable}
        self.alignments = {}

    def set_title(self, title):
        self.title = title

    def add_column(self, header, alignment='left'):
        self.columns.append(header)
        self.alignments[header] = alignment

    def add_row(self, row_data):
        if len(row_data) != len(self.columns):
            raise ValueError("Row data must match the number of columns.")
        self.rows.append(row_data)

    def add_subtable(self, row_idx, col_idx, subtable):
        self.subtables[(row_idx, col_idx)] = subtable

    def _calculate_column_widths(self):
        terminal_width = shutil.get_terminal_size((80, 20)).columns
        available_width = terminal_width - (3 * len(self.columns) + 1)  # Account for borders

        def calc_widths(table, avail_width):
            col_widths = [len(str(col)) for col in table.columns]
            
            for row in table.rows:
                for idx, cell in enumerate(row):
                    content = str(cell)
                    if (table.rows.index(row), idx) in table.subtables:
                        subtable = table.subtables[(table.rows.index(row), idx)]
                        sub_widths = calc_widths(subtable, avail_width)
                        col_widths[idx] = max(col_widths[idx], sum(sub_widths) + 3 * len(sub_widths) + 1)
                    else:
                        col_widths[idx] = max(col_widths[idx], len(content))
            
            total_width = sum(col_widths)
            if total_width > avail_width:
                scale_factor = avail_width / total_width
                col_widths = [max(math.floor(w * scale_factor), 3) for w in col_widths]
            
            return col_widths

        return calc_widths(self, available_width)

    def _render_separator(self, col_widths, sep_type='mid'):
        sep_char = {
            'top': ('┌', '┬', '┐'),
            'mid': ('├', '┼', '┤'),
            'bottom': ('└', '┴', '┘')
        }
        left, mid, right = sep_char[sep_type]
        line = left
        for idx, width in enumerate(col_widths):
            line += '─' * (width + 2)
            if idx < len(col_widths) - 1:
                line += mid
        line += right
        return line

    def render(self):
        output_lines = []

        col_widths = self._calculate_column_widths()

        # Render title
        if self.title:
            total_width = sum(col_widths) + 3 * len(col_widths) + 1
            title_line = f"{self.title}".center(total_width)
            output_lines.append(title_line)

        # Render top separator
        output_lines.append(self._render_separator(col_widths, 'top'))

        # Render headers
        header_line = '│'
        for idx, header in enumerate(self.columns):
            content = f" {header.center(col_widths[idx])} "
            header_line += content + '│'
        output_lines.append(header_line)

        # Render middle separator
        output_lines.append(self._render_separator(col_widths, 'mid'))

        # Render rows
        for row_idx, row in enumerate(self.rows):
            row_line = '│'
            row_height = 1  # Default row height
            cell_lines_list = []

            for col_idx, cell in enumerate(row):
                cell_content = str(cell)
                if (row_idx, col_idx) in self.subtables:
                    # Render subtable and get its lines
                    subtable = self.subtables[(row_idx, col_idx)]
                    sub_lines = subtable.render().split('\n')
                    # Update row height if subtable is taller
                    row_height = max(row_height, len(sub_lines))
                    cell_lines_list.append(sub_lines)
                else:
                    # Wrap text if necessary
                    wrapped_lines = self._wrap_text(
                        cell_content, col_widths[col_idx])
                    row_height = max(row_height, len(wrapped_lines))
                    cell_lines_list.append(wrapped_lines)

            # Adjust cell lines to have the same height
            adjusted_cell_lines = []
            for lines in cell_lines_list:
                if len(lines) < row_height:
                    lines.extend([''] * (row_height - len(lines)))
                adjusted_cell_lines.append(lines)

            # Render each line of the row
            for line_idx in range(row_height):
                row_line = '│'
                for col_idx, lines in enumerate(adjusted_cell_lines):
                    content = lines[line_idx]
                    alignment = self.alignments.get(
                        self.columns[col_idx], 'left')
                    formatted_content = self._format_cell(
                        content, col_widths[col_idx], alignment)
                    row_line += f" {formatted_content} │"
                output_lines.append(row_line)

        # Render bottom separator
        output_lines.append(self._render_separator(col_widths, 'bottom'))

        return '\n'.join(output_lines)

    def _wrap_text(self, text, width):
        lines = []
        while len(text) > width:
            # Find the last space within width
            split_pos = text.rfind(' ', 0, width)
            if split_pos == -1:
                split_pos = width
            lines.append(text[:split_pos])
            text = text[split_pos:].lstrip()
        lines.append(text)
        return lines

    def _format_cell(self, content, width, alignment):
        if alignment == 'left':
            return content.ljust(width)
        elif alignment == 'right':
            return content.rjust(width)
        elif alignment == 'center':
            return content.center(width)
        else:
            return content.ljust(width)
