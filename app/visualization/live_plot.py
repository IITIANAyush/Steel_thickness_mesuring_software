import matplotlib.pyplot as plt


class LivePlot:
    def __init__(self):
        self.x = []
        self.y = []

    def update(self, encoder_position, thickness):
        self.x.append(encoder_position)
        self.y.append(thickness)

        plt.clf()
        plt.plot(self.x, self.y)
        plt.pause(0.001)