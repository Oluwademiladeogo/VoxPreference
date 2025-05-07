import { useState, useRef, FormEvent, DragEvent } from "react";
import ApiService from "../services/api";
import { API_CONFIG } from "../config/api";

interface AudioUploadFormProps {
  onUploadComplete?: () => void;
}

interface ErrorState {
  message: string;
  type: "file" | "upload" | "validation" | "network";
}

const AudioUploadForm = ({ onUploadComplete }: AudioUploadFormProps) => {
  const [fileName, setFileName] = useState("");
  const [fileDescription, setFileDescription] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadResult, setUploadResult] = useState<{
    message: string;
    success: boolean;
  } | null>(null);
  const [error, setError] = useState<ErrorState | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      validateAndSetFile(files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const validateAndSetFile = (file: File) => {
    setError(null);

    if (!API_CONFIG.SUPPORTED_FILE_TYPES.includes(file.type)) {
      setError({
        message: `Please select a valid audio file (${API_CONFIG.SUPPORTED_FILE_TYPES.join(
          ", "
        )})`,
        type: "validation",
      });
      return;
    }

    if (file.size > API_CONFIG.MAX_FILE_SIZE) {
      setError({
        message: `File size exceeds ${
          API_CONFIG.MAX_FILE_SIZE / (1024 * 1024)
        }MB limit`,
        type: "validation",
      });
      return;
    }

    setSelectedFile(file);
  };

  const removeFile = () => {
    setSelectedFile(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!selectedFile) {
      setError({
        message: "Please select an audio file",
        type: "validation",
      });
      return;
    }

    if (!fileName.trim()) {
      setError({
        message: "Please provide a file name",
        type: "validation",
      });
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);
    setUploadResult(null);

    const formData = new FormData();
    formData.append("fileName", fileName);
    formData.append("fileDescription", fileDescription);
    formData.append("audioFile", selectedFile);

    try {
      await ApiService.uploadAudio(formData);
      setUploadProgress(100);
      setUploadResult({
        message: "File uploaded successfully!",
        success: true,
      });

      // Reset form after successful upload
      setTimeout(() => {
        setFileName("");
        setFileDescription("");
        setSelectedFile(null);
        setUploadProgress(0);
        setIsUploading(false);
        setUploadResult(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
        onUploadComplete?.();
      }, 3000);
    } catch (error) {
      console.error("Error:", error);
      setError({
        message:
          error instanceof Error ? error.message : "Unknown error occurred",
        type:
          error instanceof Error && error.message.includes("Network")
            ? "network"
            : "upload",
      });
      setIsUploading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto my-10 bg-white rounded-lg shadow-md p-8">
      <h1 className="text-3xl font-bold text-center text-blue-700 mb-6">
        VoxPreference Audio Upload
      </h1>
      <p className="text-center text-gray-600 mb-8">
        Upload audio files for speech recognition and analysis. Supported
        formats: WAV, MP3, FLAC, OGG (max 20MB).
      </p>

      {error && (
        <div className="mb-4 p-4 rounded-lg bg-red-50 border border-red-200">
          <div className="flex items-center">
            <svg
              className="w-5 h-5 text-red-500 mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="text-red-700">{error.message}</p>
          </div>
        </div>
      )}

      {uploadResult && (
        <div
          className={`mb-4 p-4 rounded-lg ${
            uploadResult.success
              ? "bg-green-50 border border-green-200"
              : "bg-red-50 border border-red-200"
          }`}
        >
          <div className="flex items-center">
            {uploadResult.success ? (
              <svg
                className="w-5 h-5 text-green-500 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            ) : (
              <svg
                className="w-5 h-5 text-red-500 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            )}
            <p
              className={
                uploadResult.success ? "text-green-700" : "text-red-700"
              }
            >
              {uploadResult.message}
            </p>
          </div>
        </div>
      )}

      <form
        encType="multipart/form-data"
        onSubmit={handleSubmit}
        className="space-y-6"
      >
        <div className="space-y-2">
          <label
            htmlFor="fileName"
            className="block font-semibold text-gray-700"
          >
            File Name
          </label>
          <input
            type="text"
            id="fileName"
            value={fileName}
            onChange={(e) => setFileName(e.target.value)}
            placeholder="Enter a name for your audio file"
            required
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
          />
        </div>

        <div className="space-y-2">
          <label
            htmlFor="fileDescription"
            className="block font-semibold text-gray-700"
          >
            Description
          </label>
          <textarea
            id="fileDescription"
            value={fileDescription}
            onChange={(e) => setFileDescription(e.target.value)}
            rows={4}
            placeholder="Provide some details about this audio file (optional)"
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
          />
        </div>

        <div className="space-y-2">
          <label className="block font-semibold text-gray-700">
            Audio File
          </label>
          <div
            className={`relative border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-colors duration-300 ${
              isDragging
                ? "border-blue-600 bg-blue-50"
                : "border-gray-300 bg-gray-50 hover:bg-gray-100"
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <i className="fas fa-microphone-alt text-4xl text-blue-600 mb-4 block"></i>
            <p className="font-semibold mb-2">
              Drag & Drop your audio file here
            </p>
            <p className="text-sm text-gray-600">or click to browse files</p>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept="audio/*"
              required
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />

            {selectedFile && (
              <div className="mt-4 bg-blue-50 p-3 rounded-lg flex items-center justify-between">
                <span className="text-sm">{selectedFile.name}</span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile();
                  }}
                  className="text-red-500 hover:text-red-700"
                >
                  <i className="fas fa-times"></i>
                </button>
              </div>
            )}
          </div>
        </div>

        <button
          type="submit"
          disabled={isUploading || !selectedFile}
          className={`w-full py-3 rounded-lg font-semibold transition-colors duration-300 ${
            isUploading || !selectedFile
              ? "bg-gray-400 cursor-not-allowed"
              : "bg-blue-600 hover:bg-blue-700 text-white"
          }`}
        >
          {isUploading ? "Uploading..." : "Upload Audio"}
        </button>

        {isUploading && (
          <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-600 transition-all duration-300 ease-out"
              style={{ width: `${uploadProgress}%` }}
            ></div>
          </div>
        )}
      </form>
    </div>
  );
};

export default AudioUploadForm;
