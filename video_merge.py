from moviepy.editor import VideoFileClip, CompositeAudioClip, AudioFileClip, concatenate_videoclips,concatenate_audioclips
from collections import defaultdict
from progress import progress_state
import shutil
import os



BASE_DIR = os.path.dirname(__file__)
LOGO_PATH = os.path.join(BASE_DIR, "assets", "Myntra Updated Logo.MOV")


def group_and_copy_videos_by_sku(extracted_path, session_path):
    batches = [
        os.path.join(extracted_path, d)
        for d in os.listdir(extracted_path)
        if os.path.isdir(os.path.join(extracted_path, d))
    ]

    print("Found batches:", batches)

    grouped = defaultdict(list)

    for batch_path in batches:
        batch_name = os.path.basename(batch_path).lower().replace(" ", "_")
        for fname in os.listdir(batch_path):
            if not fname.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                continue
            sku = os.path.splitext(fname)[0]
            full_path = os.path.join(batch_path, fname)
            if f"_{batch_name}" not in fname.lower():
                grouped[sku].append((full_path, batch_name))

    print("SKU grouping:")
    for sku, files in grouped.items():
        print(f"  {sku}: {[f[0] for f in files]}")

    tmp_root = os.path.join(session_path, "by_sku")
    os.makedirs(tmp_root, exist_ok=True)

    for sku, filepaths in grouped.items():
        sku_folder = os.path.join(tmp_root, sku)
        os.makedirs(sku_folder, exist_ok=True)
        for fpath, batch_name in filepaths:
            ext = os.path.splitext(fpath)[1]
            batch_suffix = batch_name.replace("batch_", "").replace("batch", "").strip()
            new_filename = f"{sku}_batch_{batch_suffix}{ext}"
            dest_path = os.path.join(sku_folder, new_filename)
            shutil.copy(fpath, dest_path)

    print("Files copied into SKU folders:")
    for sku_folder in os.listdir(tmp_root):
        path = os.path.join(tmp_root, sku_folder)
        print(f"  {sku_folder}: {os.listdir(path)}")

    return tmp_root

def merge_videos_from_folder(folder_path: str, output_folder: str, audio_file: str = None) -> list:
    os.makedirs(output_folder, exist_ok=True)
    merged_videos = []
    logo_path = 'Myntra Updated Logo.MOV'

    sku_folders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
    total = len(sku_folders)
    progress_state["done"] = False  # reset progress

    for idx, sku_folder in enumerate(sku_folders):
        sku_path = os.path.join(folder_path, sku_folder)

        video_files = sorted([
            f for f in os.listdir(sku_path)
            if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')) and '_batch_' in f
        ], key=lambda x: int(x.split('_batch_')[-1].split('.')[0]))

        print(f"Merging videos for SKU {sku_folder}: {video_files}")
        if not video_files:
            print(f"No valid batch videos for SKU {sku_folder}, skipping.")
            continue

        # Update progress
        progress_state["percent"] = int((idx + 1) / total * 100)
        progress_state["message"] = f"Merging {sku_folder} ({idx + 1}/{total})"

        clips = []
        try:
            for vf in video_files:
                clip = VideoFileClip(os.path.join(sku_path, vf))
                clips.append(clip)

            if logo_path and os.path.exists(logo_path):
                logo_clip = VideoFileClip(logo_path)
                clips.append(logo_clip)

            final_clip = concatenate_videoclips(clips, method="compose")

            output_path = os.path.join(output_folder, f"{sku_folder}.mp4")

            if audio_file and os.path.exists(audio_file):
                audioclip = AudioFileClip(audio_file)

                if audioclip.duration < final_clip.duration:
                    n_loops = int(final_clip.duration // audioclip.duration) + 1
                    audioclip = concatenate_audioclips([audioclip] * n_loops)

                audioclip = audioclip.subclip(0, final_clip.duration)
                final_clip = final_clip.set_audio(CompositeAudioClip([audioclip]))

            final_clip.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
                preset="ultrafast",
                threads=2,
                remove_temp=True,
                verbose=False
            )

            merged_videos.append(output_path)

        except Exception as e:
            print(f"Error processing {sku_folder}: {e}")
        finally:
            for clip in clips:
                clip.close()
            if 'final_clip' in locals():
                final_clip.close()
            if logo_path and 'logo_clip' in locals():
                logo_clip.close()
            if audio_file and 'audioclip' in locals():
                audioclip.close()

    progress_state["done"] = True
    progress_state["message"] = "All videos merged!"
    print("Final merged videos:", merged_videos)
    return merged_videos




