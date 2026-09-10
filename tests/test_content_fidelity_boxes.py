import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from native.host import prepare_reflowable_boxes


@unittest.skipUnless(shutil.which('pandoc'), 'Pandoc required')
class ContentBoxTests(unittest.TestCase):
    def test_graphic_and_captioned_table_content_survive_print_boxes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/'main.tex'
            path.write_text(r'''\documentclass{article}\begin{document}
\begin{figure}\makebox[\textwidth][c]{\begin{tabular}{c}\includegraphics{plot.png}\end{tabular}}
\caption{Graphic content}\label{fig:plot}\end{figure}
\begin{table}\caption{Complete explanatory table caption}\label{tbl:values}
\begin{tabular}{lc}\makecell[c]{Answer \\ Value} & Probability \\ Paris & \raisebox{-0.1cm}{0.9} \\ \end{tabular}
\end{table}\end{document}''')
            self.assertEqual(prepare_reflowable_boxes(root),3)
            result=subprocess.run(['pandoc',str(path),'-f','latex','-t','html5'],text=True,capture_output=True,check=True)
            self.assertIn('src="plot.png"',result.stdout)
            self.assertIn('<caption>Complete explanatory table caption</caption>',result.stdout)
            self.assertIn('Paris',result.stdout)
            self.assertIn('0.9',result.stdout)
            self.assertNotIn('class="tabular"',result.stdout)
            self.assertIn('<br',result.stdout)
            self.assertEqual(prepare_reflowable_boxes(root),0)

    def test_comments_and_picture_coordinate_boxes_remain_untouched(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/'main.tex'
            original='% \\makebox[3cm]{comment}\n'+r'\makebox(10,20){picture}'
            path.write_text(original)
            self.assertEqual(prepare_reflowable_boxes(root),0)
            self.assertEqual(path.read_text(),original)
