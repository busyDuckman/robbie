from PySide2.QtWidgets import QApplication, QWidget, \
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QDoubleSpinBox

from PySide2.QtCore import Qt
import sys
import numpy as np

from pose_and_IK import calculate_pose

def make_spin_box(val, dp=2):
    qsb =QDoubleSpinBox()
    qsb.setMinimum(-10_000)
    qsb.setMaximum(10_000)
    qsb.setValue(val)
    qsb.setDecimals(dp)
    return qsb


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setGeometry(300, 300, 800, 600)
        self.setWindowTitle('3-DOF Platform Pose Calculator')

        self.main_layout = QHBoxLayout()
        self.setLayout(self.main_layout)

        self.input_layout = QVBoxLayout()
        self.main_layout.addLayout(self.input_layout, 1)

        self.input_layout.addWidget(QLabel('Geometry:'))

        self.r1_input = make_spin_box(80)
        self.input_layout.addWidget(QLabel('R1 (base):'))
        self.input_layout.addWidget(self.r1_input)

        self.r2_input = make_spin_box(60)
        self.input_layout.addWidget(QLabel('R2 (platform):'))
        self.input_layout.addWidget(self.r2_input)

        self.rod_len_input = make_spin_box(500)
        self.input_layout.addWidget(QLabel('L (rod length):'))
        self.input_layout.addWidget(self.rod_len_input)

        self.input_layout.addWidget(QLabel('Sled Positions (deg):'))
        self.theta1_input = make_spin_box(0)
        self.input_layout.addWidget(QLabel('Theta 1:'))
        self.input_layout.addWidget(self.theta1_input)
        self.theta2_input = make_spin_box(160)
        self.input_layout.addWidget(QLabel('Theta 2:'))
        self.input_layout.addWidget(self.theta2_input)
        self.theta3_input = make_spin_box(240)
        self.input_layout.addWidget(QLabel('Theta 3:'))
        self.input_layout.addWidget(self.theta3_input)

        self.calculate_button = QPushButton('Calculate Pose')
        self.calculate_button.clicked.connect(self.update_pose)
        self.input_layout.addWidget(self.calculate_button)

        self.input_layout.addWidget(QLabel('Platform Pose:'))
        self.pose_label = QLabel()
        self.input_layout.addWidget(self.pose_label)

        self.view_layout = QVBoxLayout()
        self.main_layout.addLayout(self.view_layout, 3)

        self.view_placeholder = QLabel('3D View Placeholder')
        self.view_placeholder.setAlignment(Qt.AlignCenter)
        self.view_layout.addWidget(self.view_placeholder)

    def update_pose(self):
        try:
            r1 = self.r1_input.value()
            r2 = self.r1_input.value()
            rod_len = self.rod_len_input.value()
            theta1 = self.theta1_input.value()
            theta2 = self.theta2_input.value()
            theta3 = self.theta3_input.value()

            x_center, y_center, roll, pitch, yaw = calculate_pose(R, L, theta1, theta2, theta3)

            self.pose_label.setText(f"Center: ({x_center}, {y_center}), \m"
                                    f"Orientation: (roll: {roll}, pitch: {pitch}, yaw: {yaw})")
        except Exception as ex:
            print(ex)
            self.pose_label.setText("error")

def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
