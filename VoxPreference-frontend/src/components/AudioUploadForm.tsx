import { useState, useRef, FormEvent, DragEvent } from 'react';

const AudioUploadForm = () => {
  const [fileName, setFileName] = useState('');
  const [fileDescription, setFileDescription] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadResult, setUploadResult] = useState<{ message: string; success: boolean } | null>(null);
  
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
    const validTypes = ['audio/wav', 'audio/mpeg', 'audio/mp3', 'audio/ogg', 'audio/flac'];
    
    if (!validTypes.includes(file.type)) {
      alert('Please select a valid audio file (WAV, MP3, FLAC, OGG)');
      return;
    }
    
    if (file.size > 20 * 1024 * 1024) { // 20MB
      alert('File size exceeds 20MB limit');
      return;
    }
    
    setSelectedFile(file);
  };

  const removeFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    
    if (!selectedFile) {
      alert('Please select an audio file');
      return;
    }
    
    setIsUploading(true);
    setUploadProgress(0);
    setUploadResult(null);
    
    const formData = new FormData();
    formData.append('fileName', fileName);
    formData.append('fileDescription', fileDescription);
    formData.append('audioFile', selectedFile);
    
    try {
      const response = await fetch('http://localhost:3000/api/upload-audio', {
        method: 'POST',
        body: formData,
      });
      
      setUploadProgress(100);
      
      if (response.ok) {
        const data = await response.json();
        console.log(data)
        setUploadResult({ message: 'File uploaded successfully!', success: true });
        
        // Reset form after successful upload
        setTimeout(() => {
          setFileName('');
          setFileDescription('');
          setSelectedFile(null);
          setUploadProgress(0);
          setIsUploading(false);
          setUploadResult(null);
          if (fileInputRef.current) {
            fileInputRef.current.value = '';
          }
        }, 3000);
      } else {
        throw new Error('Upload failed');
      }
    } catch (error) {
      console.error('Error:', error);
      setUploadResult({ 
        message: `Upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`, 
        success: false 
      });
      setIsUploading(false);
    }
  };

  return (
    
    <div className="max-w-3xl mx-auto my-10 bg-white rounded-lg shadow-md p-8">
      <h1 className="text-3xl font-bold text-center text-blue-700 mb-6">VoxPreference Audio Upload</h1>
      <p className="text-center text-gray-600 mb-8">
        Upload audio files for speech recognition and analysis. Supported formats: WAV, MP3, FLAC, OGG (max 20MB).
      </p>
      
      <form encType="multipart/form-data" onSubmit={handleSubmit} className="space-y-6">
        <div className="space-y-2">
          <label htmlFor="fileName" className="block font-semibold text-gray-700">
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
          <label htmlFor="fileDescription" className="block font-semibold text-gray-700">
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
              isDragging ? 'border-blue-600 bg-blue-50' : 'border-gray-300 bg-gray-50 hover:bg-gray-100'
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <i className="fas fa-microphone-alt text-4xl text-blue-600 mb-4 block"></i>
            <p className="font-semibold mb-2">Drag & Drop your audio file here</p>
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
              ? 'bg-gray-400 cursor-not-allowed' 
              : 'bg-blue-600 hover:bg-blue-700 text-white'
          }`}
        >
          {isUploading ? 'Uploading...' : 'Upload Audio'}
        </button>
        
        {isUploading && (
          <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
            <div 
              className="h-full bg-blue-600 transition-all duration-300 ease-out"
              style={{ width: `${uploadProgress}%` }}
            ></div>
          </div>
        )}
        
        {uploadResult && (
          <div className={`p-4 rounded-lg ${
            uploadResult.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
          }`}>
            {uploadResult.message}
          </div>
        )}
      </form>
    </div>
  );
};

export default AudioUploadForm;