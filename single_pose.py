import sys
import cv2
import mediapipe as mp

IMAGE_PATH = "./wikiart/Abstract_Expressionism/andy-warhol_oxidation-painting-1978-1.jpg"

def draw_pose_on_image(image_path: str) -> None:
    image_bgr = cv2.imread(image_path)
    if image_bgr is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    annotated = image_bgr.copy()

    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    mp_styles = mp.solutions.drawing_styles

    with mp_pose.Pose(static_image_mode=True,
                      model_complexity=1,
                      enable_segmentation=False,
                      min_detection_confidence=0.5) as pose:
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        results = pose.process(image_rgb)

        if not results.pose_landmarks:
            print("No pose detected.")
        else:
            mp_drawing.draw_landmarks(
                annotated,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=mp_styles.get_default_pose_landmarks_style(),
                # fallback: just use a generic connection style
                connection_drawing_spec=mp_drawing.DrawingSpec(color=(0,255,0), thickness=2, circle_radius=2)
            )

    cv2.imshow("Pose Detection", annotated)
    print("Press any key in the image window to close.")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":

    draw_pose_on_image(IMAGE_PATH)
