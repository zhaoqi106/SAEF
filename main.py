from PySide6 import QtWidgets
from PySide6.QtGui import QImage, QPixmap
from UI.SelectUI import Ui_Form
from rPPGCollectTool import rPPGCollectTool
from PostAlg import PostAlg
from Demo import Demo


class Main(QtWidgets.QWidget, Ui_Form):
    def __init__(self):
        super(Main, self).__init__()
        self.setupUi(self)

        self.setWindowTitle("rPPGCollectTool V2.0.0")

        self.btn_dc.clicked.connect(self.showDC)
        self.btn_pp.clicked.connect(self.showPP)
        self.btn_demo.clicked.connect(self.showDemo)

        self.m_rppg_collect_tool = None
        self.m_post_alg = None
        self.m_demo = None

    def showDC(self):
        self.m_rppg_collect_tool = rPPGCollectTool()
        self.m_rppg_collect_tool.show()
        self.close()

    def showPP(self):
        self.m_post_alg = PostAlg()
        self.m_post_alg.show()
        self.close()

    def showDemo(self):
        self.m_demo = Demo()
        self.m_demo.show()
        self.close()

if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication(sys.argv)
    demo = Main()
    demo.show()
    sys.exit(app.exec_())