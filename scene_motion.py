"""Short-interval scene evidence with global exposure compensation."""


def motion_evidence(frames, max_gap=7.5, width=320, diff_thr=18):
    """frames: [(capture_timestamp, JPEG bytes)]. Missing coverage is not quiet evidence."""
    import cv2
    import numpy as np
    grays = []
    for timestamp, jpeg in sorted(frames, key=lambda x: x[0]):
        try:
            image = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                continue
            h, w = image.shape[:2]
            gray = cv2.cvtColor(cv2.resize(image, (width, max(1, round(h*width/w)))), cv2.COLOR_BGR2GRAY)
            # Camera OSD timestamp is not physical motion in the room.
            gray = gray[max(1, round(gray.shape[0]*.06)):].astype(np.float32)
            grays.append((float(timestamp), gray))
        except (ValueError, cv2.error):
            continue
    raw, corrected, gaps = [], [], []
    for (ta, a), (tb, b) in zip(grays, grays[1:]):
        gap = tb-ta
        if gap <= 0 or gap > max_gap or a.shape != b.shape:
            continue
        gain, offset = 1., float(np.median(b-a))
        for _ in range(3):
            error = b-(gain*a+offset)
            keep = np.abs(error) <= max(5., float(np.percentile(np.abs(error), 75)))
            x, y = a[keep], b[keep]
            if x.size < 16:
                break
            if np.std(x) > 5:
                gain = float(np.clip(np.mean((x-x.mean())*(y-y.mean()))/(np.var(x)+1e-6), .5, 2))
            offset = float(np.median(y-gain*x))
        raw.append(float((np.abs(b-a)>diff_thr).mean()))
        corrected.append(float((np.abs(b-(gain*a+offset))>diff_thr).mean()))
        gaps.append(gap)
    return {'method': 'adjacent_exposure_v1', 'pairs': len(corrected),
            'raw_max': round(max(raw), 5) if raw else None,
            'score': round(max(corrected), 5) if corrected else None,
            'frames': len(grays), 'span_seconds': round(grays[-1][0]-grays[0][0], 2) if len(grays)>1 else 0,
            'first_at': grays[0][0] if grays else None, 'last_at': grays[-1][0] if grays else None,
            'max_pair_gap': round(max(gaps), 2) if gaps else None}
