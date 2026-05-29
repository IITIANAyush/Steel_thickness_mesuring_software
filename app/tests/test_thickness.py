from app.processing.thickness import compute_thickness



def test_thickness():
    assert compute_thickness(10) == 10
    assert compute_thickness(10, 2, 1) == 21