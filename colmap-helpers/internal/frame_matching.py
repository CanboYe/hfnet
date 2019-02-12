import cv2
import numpy as np
from matplotlib import pyplot as plt


def baseline_sift_matching(img1, img2):
    # Initiate SIFT detector
    sift = cv2.xfeatures2d.SIFT_create()

    # find the keypoints and descriptors with SIFT
    kp1, des1 = sift.detectAndCompute(img1,None)
    kp2, des2 = sift.detectAndCompute(img2,None)

    # BFMatcher with default params
    bf = cv2.BFMatcher()
    matches = bf.knnMatch(des1,des2, k=2)

    # Apply ratio test
    good = []
    for m,n in matches:
        if m.distance < 0.7*n.distance:
            good.append([m])

    # cv2.drawMatchesKnn expects list of lists as matches.
    draw_params = dict(matchColor = (0,255,0),
                       singlePointColor = (255,0,0),
                       matchesMask = None, flags = 0)
    img3 = cv2.drawMatchesKnn(img1,kp1,img2,kp2,good, None,**draw_params)
    return img3


def debug_matching(frame1, frame2, path_image1, path_image2, matches,
                   matches_mask, num_points, use_ratio_test):
    img1 = cv2.imread(path_image1, 0)
    img2 = cv2.imread(path_image2, 0)

    scaling1 = np.array(img1.shape)[::-1] / np.array(frame1['image_size']).astype(np.float)
    scaling2 = np.array(img2.shape)[::-1] / np.array(frame2['image_size']).astype(np.float)

    kp1 = frame1['keypoints'][:num_points,:] * scaling1
    kp2 = frame2['keypoints'][:num_points,:] * scaling2

    cvkp1 = get_ocv_kpts_from_np(kp1)
    cvkp2 = get_ocv_kpts_from_np(kp2)

    if use_ratio_test:
        draw_params = dict(matchColor = (0,255,0),
        singlePointColor = (255,0,0),
        matchesMask = matches_mask, flags = 0)
        img = cv2.drawMatchesKnn(img1, cvkp1, img2, cvkp2, matches, None,
        **draw_params)
    else:
        draw_params = dict(matchColor = (0,255,0),
        singlePointColor = (255,0,0), flags = 0)
        img = cv2.drawMatches(img1, cvkp1, img2, cvkp2, matches, None,
                              **draw_params)

    img_sift = baseline_sift_matching(img1, img2)

    fig = plt.figure(figsize=(2, 1))
    fig.add_subplot(2, 1, 1)
    plt.imshow(img)
    plt.title('Custom features')
    fig.add_subplot(2, 1, 2)
    plt.imshow(img_sift)
    plt.title('SIFT')
    plt.show()


def get_ocv_kpts_from_np(numpy_keypoints):
    ocv_keypoints = []
    for keypoint in numpy_keypoints:
      ocv_keypoints.append(cv2.KeyPoint(x=keypoint[0], y=keypoint[1], _size=1))

    return ocv_keypoints


def match_frames(path_npz1, path_npz2, path_image1, path_image2, num_points,
                 use_ratio_test, ratio_test_values, debug):
    frame1 = np.load(path_npz1)
    frame2 = np.load(path_npz2)

    # Assert the keypoints are sorted according to the score.
    assert np.all(np.sort(frame1['scores'])[::-1] == frame1['scores'])

    # WARNING: scores are not taken into account as of now.
    des1 = frame1['descriptors'].astype('float32')[:num_points,:]
    des2 = frame2['descriptors'].astype('float32')[:num_points,:]

    if use_ratio_test:
        keypoint_matches = [[] for i in ratio_test_values]
        matcher = cv2.BFMatcher(cv2.NORM_L2)
        matches = matcher.knnMatch(des1, des2, k=2)

        smallest_distances = [dict() for x in ratio_test_values]

        # Ratio test as per Lowe's paper.
        matches_mask = [[0,0] for i in xrange(len(matches))]
        for i,(m,n) in enumerate(matches):
            for ratio_idx, ratio in enumerate(ratio_test_values):
                if m.distance < ratio * n.distance:
                    if m.trainIdx not in smallest_distances[ratio_idx]:
                      smallest_distances[ratio_idx][m.trainIdx] = (m.distance, m.queryIdx)
                      matches_mask[i] = [1,0]
                      keypoint_matches[ratio_idx].append((m.queryIdx, m.trainIdx))
                    else:
                      old_dist, old_queryIdx = smallest_distances[ratio_idx][m.trainIdx]
                      if m.distance < old_dist:
                        old_distance, old_queryIdx = smallest_distances[ratio_idx][m.trainIdx]
                        smallest_distances[ratio_idx][m.trainIdx] = (m.distance, m.queryIdx)
                        matches_mask[i] = [1,0]
                        keypoint_matches[ratio_idx].remove((old_queryIdx, m.trainIdx))
                        keypoint_matches[ratio_idx].append((m.queryIdx, m.trainIdx))
    else:
        keypoint_matches = [[]]
        matches_mask = []
        matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=True)
        matches = matcher.match(des1, des2)

        # Matches are already cross-checked.
        for match in matches:
            # match.trainIdx belongs to des2.
            keypoint_matches[0].append((match.queryIdx, match.trainIdx))

    if debug:
        debug_matching(frame1, frame2, path_image1, path_image2, matches,
                       matches_mask, num_points, use_ratio_test)

    return keypoint_matches