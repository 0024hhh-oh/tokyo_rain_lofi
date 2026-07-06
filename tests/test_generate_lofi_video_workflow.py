from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/generate_lofi_video.yml"


def workflow_text() -> str:
    return WORKFLOW.read_text()


def test_workflow_dispatch_keeps_drive_folder_id_as_debug_only_input():
    text = workflow_text()

    assert "workflow_dispatch:" in text
    assert "      DRIVE_FOLDER_ID:" in text
    assert 'description: "デバッグ用: 指定したDriveフォルダIDを直接処理（通常は空）"' in text
    assert 'default: ""' in text
    assert 'description: "デバッグ用: Driveの video_XXX 番号（DRIVE_FOLDER_IDもincomingも未使用時のみ）"' in text
    assert 'description: "デバッグ用: 完成MP4ファイル名（通常はincomingフォルダ名から自動設定）"' in text
    assert 'description: "デバッグ用: YouTube動画タイトル（通常はincomingフォルダ名から自動設定）"' in text
    assert "required: false" in text


def test_debug_metadata_defaults_are_blank_so_incoming_outputs_are_used():
    text = workflow_text()

    assert 'default: "Tokyo_Memory_Archive_001.mp4"' not in text
    assert 'default: "Tokyo Memory Archive 001 - Tokyo ChillMatic FM"' not in text
    assert 'OUTPUT_FILE: ${{ inputs.output_file || steps.incoming.outputs.output_file }}' in text
    assert 'YOUTUBE_TITLE: ${{ inputs.youtube_title || steps.incoming.outputs.youtube_title }}' in text


def test_workflow_dispatch_without_drive_folder_uses_incoming_queue():
    text = workflow_text()

    detect_condition = "if: ${{ github.event_name != 'workflow_dispatch' || inputs.DRIVE_FOLDER_ID == '' }}"
    stop_condition = "if: ${{ (github.event_name != 'workflow_dispatch' || inputs.DRIVE_FOLDER_ID == '') && steps.incoming.outputs.found != 'true' }}"
    runnable_condition = "if: ${{ inputs.DRIVE_FOLDER_ID != '' || steps.incoming.outputs.found == 'true' }}"

    assert detect_condition in text
    assert stop_condition in text
    assert text.count(runnable_condition) >= 4


def test_workflow_resolves_drive_folder_id_only_from_explicit_debug_input():
    text = workflow_text()

    assert "WORKFLOW_DISPATCH_DRIVE_FOLDER_ID: ${{ inputs.DRIVE_FOLDER_ID || '' }}" in text
    assert "RESOLVED_DRIVE_FOLDER_ID: ${{ inputs.DRIVE_FOLDER_ID || '' }}" in text
    assert "INCOMING_WORK_FOLDER_ID: ${{ steps.incoming.outputs.work_folder_id || '' }}" in text
    assert "DRIVE_FOLDER_ID: ${{ inputs.DRIVE_FOLDER_ID || steps.incoming.outputs.work_folder_id }}" not in text
    assert 'if [[ -n "${RESOLVED_DRIVE_FOLDER_ID}" ]]; then' in text
    assert '--drive-folder-id "${RESOLVED_DRIVE_FOLDER_ID}"' in text
    assert 'elif [[ -n "${INCOMING_WORK_FOLDER_ID}" ]]; then' in text
    assert '--drive-folder-id "${INCOMING_WORK_FOLDER_ID}"' in text


def test_workflow_logs_debug_inputs_and_selected_acquisition_method_before_download():
    text = workflow_text()

    log_workflow_dispatch_drive_folder_id = 'echo "workflow_dispatch DRIVE_FOLDER_ID=${WORKFLOW_DISPATCH_DRIVE_FOLDER_ID}"'
    log_resolved_drive_folder_id = 'echo "resolved DRIVE_FOLDER_ID=${RESOLVED_DRIVE_FOLDER_ID}"'
    log_incoming_work_folder_id = 'echo "incoming selected work_folder_id=${INCOMING_WORK_FOLDER_ID}"'
    log_video_number = 'echo "VIDEO_NUMBER=${VIDEO_NUMBER}"'
    log_drive_method = 'echo "asset acquisition method=drive-folder-id"'
    log_incoming_method = 'echo "asset acquisition method=incoming-queue"'
    first_download = text.index("--drive-folder-id")

    for log_line in [
        log_workflow_dispatch_drive_folder_id,
        log_resolved_drive_folder_id,
        log_incoming_work_folder_id,
        log_video_number,
    ]:
        assert log_line in text
        assert text.index(log_line) < first_download

    assert log_drive_method in text
    assert text.index(log_drive_method) < first_download
    assert log_incoming_method in text
    assert text.index(log_incoming_method) < text.rindex("--drive-folder-id")


def test_drive_folder_id_branch_does_not_use_video_number_argument():
    text = workflow_text()

    drive_branch = text.split('if [[ -n "${RESOLVED_DRIVE_FOLDER_ID}" ]]; then', 1)[1].split("elif", 1)[0]

    assert "--drive-folder-id" in drive_branch
    assert "--video-number" not in drive_branch


def test_blank_workflow_dispatch_drive_folder_id_does_not_enter_drive_folder_id_branch():
    text = workflow_text()

    assert "RESOLVED_DRIVE_FOLDER_ID: ${{ inputs.DRIVE_FOLDER_ID || '' }}" in text
    assert "RESOLVED_DRIVE_FOLDER_ID: ${{ inputs.DRIVE_FOLDER_ID || steps.incoming.outputs.work_folder_id }}" not in text
    assert "DRIVE_FOLDER_ID: ${{ inputs.DRIVE_FOLDER_ID || steps.incoming.outputs.work_folder_id }}" not in text

    drive_branch = text.split('if [[ -n "${RESOLVED_DRIVE_FOLDER_ID}" ]]; then', 1)[1].split("elif", 1)[0]
    incoming_branch = text.split('elif [[ -n "${INCOMING_WORK_FOLDER_ID}" ]]; then', 1)[1].split("else", 1)[0]

    assert 'asset acquisition method=drive-folder-id' in drive_branch
    assert 'INCOMING_WORK_FOLDER_ID' not in drive_branch
    assert 'asset acquisition method=incoming-queue' in incoming_branch
    assert '--drive-folder-id "${INCOMING_WORK_FOLDER_ID}"' in incoming_branch


def test_workflow_moves_successful_incoming_work_to_completed():
    text = workflow_text()

    assert "Move incoming work to completed" in text
    assert "--destination completed" in text
    assert "Move incoming work to processed" not in text
    assert "--destination processed" not in text
