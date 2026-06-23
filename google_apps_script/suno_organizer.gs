/**
 * SUNO mp3 organizer for Tokyo ChillMatic FM.
 *
 * Google Drive folder structure:
 * Tokyo ChillMatic FM/
 *   Incoming/  ... source mp3 files
 *   Videos/    ... destination video_XXX folders
 *
 * Run this function from Apps Script or the mobile Apps Script app shortcut.
 */
function runSunoOrganizer() {
  const ROOT_FOLDER_NAME = 'Tokyo ChillMatic FM';
  const INCOMING_FOLDER_NAME = 'Incoming';
  const VIDEOS_FOLDER_NAME = 'Videos';
  const BATCH_SIZE = 20;
  const VIDEO_FOLDER_PREFIX = 'video_';

  const rootFolder = getSingleFolderByName_(ROOT_FOLDER_NAME, DriveApp.getRootFolder());
  const incomingFolder = getSingleFolderByName_(INCOMING_FOLDER_NAME, rootFolder);
  const videosFolder = getSingleFolderByName_(VIDEOS_FOLDER_NAME, rootFolder);

  const mp3FileRecords = listMp3FileRecords_(incomingFolder);
  Logger.log('Incoming内のmp3数: %s', mp3FileRecords.length);

  if (mp3FileRecords.length < BATCH_SIZE) {
    Logger.log('20曲未満のため処理なし');
    return;
  }

  let nextVideoNumber = getNextVideoNumber_(videosFolder, VIDEO_FOLDER_PREFIX);
  let processedBatches = 0;

  while (mp3FileRecords.length >= BATCH_SIZE) {
    const videoFolderName = VIDEO_FOLDER_PREFIX + String(nextVideoNumber).padStart(3, '0');
    const videoFolder = videosFolder.createFolder(videoFolderName);
    const tracksFolder = videoFolder.createFolder('tracks');
    const batchFileRecords = mp3FileRecords.splice(0, BATCH_SIZE);

    Logger.log('作成フォルダ: Videos/%s/tracks', videoFolderName);

    batchFileRecords.forEach(function(record, index) {
      const file = DriveApp.getFileById(record.id);
      const trackName = 'track' + String(index + 1).padStart(2, '0') + '.mp3';
      Logger.log(
        '移動: ID=%s / 元ファイル名=%s -> %s/%s',
        record.id,
        record.originalName,
        videoFolderName,
        'tracks/' + trackName
      );
      file.setName(trackName);
      file.moveTo(tracksFolder);
    });

    Logger.log('%s に20曲を移動しました', videoFolderName);
    processedBatches += 1;
    nextVideoNumber += 1;
  }

  Logger.log('処理完了: %sバッチ / %s曲を整理しました', processedBatches, processedBatches * BATCH_SIZE);
  Logger.log('Incomingに残ったmp3数: %s', mp3FileRecords.length);
}

function getSingleFolderByName_(folderName, parentFolder) {
  const folders = parentFolder.getFoldersByName(folderName);
  if (!folders.hasNext()) {
    throw new Error('フォルダが見つかりません: ' + folderName);
  }

  const folder = folders.next();
  if (folders.hasNext()) {
    throw new Error('同名フォルダが複数あります。整理してから再実行してください: ' + folderName);
  }

  return folder;
}

function listMp3FileRecords_(folder) {
  const records = [];
  const iterator = folder.getFiles();

  while (iterator.hasNext()) {
    const file = iterator.next();
    if (file.getName().toLowerCase().endsWith('.mp3')) {
      records.push({
        id: file.getId(),
        originalName: file.getName(),
        createdTime: file.getDateCreated().getTime(),
      });
    }
  }

  records.sort(function(a, b) {
    const createdDiff = a.createdTime - b.createdTime;
    if (createdDiff !== 0) {
      return createdDiff;
    }
    return a.id.localeCompare(b.id);
  });

  return records;
}

function getNextVideoNumber_(videosFolder, prefix) {
  let maxNumber = 0;
  const folders = videosFolder.getFolders();
  const pattern = new RegExp('^' + prefix + '(\\d{3,})$');

  while (folders.hasNext()) {
    const folder = folders.next();
    const match = folder.getName().match(pattern);
    if (match) {
      maxNumber = Math.max(maxNumber, Number(match[1]));
    }
  }

  return maxNumber + 1;
}
