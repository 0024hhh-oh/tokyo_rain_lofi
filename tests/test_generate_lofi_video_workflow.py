from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/generate_lofi_video.yml"


def workflow_text() -> str:
    return WORKFLOW.read_text()


def test_workflow_dispatch_exposes_drive_folder_id_input():
    text = workflow_text()

    assert "workflow_dispatch:" in text
    assert "      DRIVE_FOLDER_ID:" in text
    assert 'description: "Driveの取得対象フォルダID（指定時はvideo_numberを使わない）"' in text
    assert 'default: ""' in text


def test_workflow_dispatch_drive_folder_id_is_passed_to_download_script():
    text = workflow_text()

    assert "WORKFLOW_DISPATCH_DRIVE_FOLDER_ID: ${{ inputs.DRIVE_FOLDER_ID || '' }}" in text
    assert (
        "DRIVE_FOLDER_ID: ${{ github.event_name == 'workflow_dispatch' && inputs.DRIVE_FOLDER_ID || "
        "steps.incoming.outputs.work_folder_id }}"
        in text
    )
    assert 'if [[ -n "${DRIVE_FOLDER_ID}" ]]; then' in text
    assert "--drive-folder-id \"${DRIVE_FOLDER_ID}\"" in text


def test_workflow_logs_inputs_and_selected_acquisition_method_before_download():
    text = workflow_text()

    log_input = 'echo "workflow_dispatch inputs: DRIVE_FOLDER_ID=${WORKFLOW_DISPATCH_DRIVE_FOLDER_ID} video_number=${WORKFLOW_DISPATCH_VIDEO_NUMBER}"'
    log_drive_folder_id = 'echo "DRIVE_FOLDER_ID=${DRIVE_FOLDER_ID}"'
    log_video_number = 'echo "VIDEO_NUMBER=${VIDEO_NUMBER}"'
    log_drive_method = 'echo "asset acquisition method=drive-folder-id"'
    log_video_method = 'echo "asset acquisition method=video-number"'
    drive_download = text.index("--drive-folder-id")
    video_download = text.index("--video-number")

    for log_line in [log_input, log_drive_folder_id, log_video_number]:
        assert log_line in text
        assert text.index(log_line) < drive_download
        assert text.index(log_line) < video_download

    assert log_drive_method in text
    assert text.index(log_drive_method) < drive_download
    assert log_video_method in text
    assert text.index(log_video_method) < video_download


def test_drive_folder_id_branch_does_not_use_video_number_argument():
    text = workflow_text()

    drive_branch = text.split('if [[ -n "${DRIVE_FOLDER_ID}" ]]; then', 1)[1].split("else", 1)[0]

    assert "--drive-folder-id" in drive_branch
    assert "--video-number" not in drive_branch
