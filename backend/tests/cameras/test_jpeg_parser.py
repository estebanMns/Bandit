from bandit.cameras.infrastructure.jpeg_parser import JpegStreamParser

FIRST = b"\xff\xd8primero\xff\xd9"
SECOND = b"\xff\xd8segundo\xff\xd9"


def test_extracts_multiple_frames_from_one_chunk():
    assert JpegStreamParser().feed(FIRST + SECOND) == [FIRST, SECOND]


def test_reassembles_a_frame_split_across_chunks():
    parser = JpegStreamParser()

    assert parser.feed(FIRST[:5]) == []
    assert parser.feed(FIRST[5:]) == [FIRST]


def test_discards_bytes_before_the_start_marker():
    assert JpegStreamParser().feed(b"basura" + FIRST) == [FIRST]


def test_oversized_incomplete_frame_does_not_grow_without_limit():
    parser = JpegStreamParser(max_buffer_bytes=16)

    assert parser.feed(b"\xff\xd8" + b"a" * 64) == []
    assert parser.feed(FIRST) == [FIRST]
