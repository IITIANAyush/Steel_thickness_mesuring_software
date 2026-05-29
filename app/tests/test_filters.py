from app.processing.filters import MovingAverageFilter



def test_moving_average_filter():
    f = MovingAverageFilter(window_size=3)

    assert f.apply(1) == 1
    assert f.apply(2) == 1.5
    assert f.apply(3) == 2