import { TextToolBoxKeys } from "../enums/text-tool-box-keys.enum";

export const selectedKeysNames = {
  [TextToolBoxKeys.textToolBoxToSummary]: 'Audio Summary',
  [TextToolBoxKeys.textToolBoxToTranscription]: 'Audio Transcription',
  [TextToolBoxKeys.textToolBoxToDocFile]: 'To Doc File',
 } as Record<string, string>;
