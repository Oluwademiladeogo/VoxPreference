import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../components/Header.jsx";
import Footer from "../components/Footer.jsx";
import ProgressBar from "../components/ProgressBar.jsx";
import Audio from "../assets/Audio.svg";

function formatFileSize(bytes) {
  if (!bytes) return "0 KB";
  return `${(bytes / 1024).toFixed(1)} KB`;
}

export default function UploadPage() {
  const [audioFiles, setAudioFiles] = useState([]);
  const [error, setError] = useState("");
  const fileInputRef = useRef();
  const navigate = useNavigate();

  function acceptFiles(files) {
    const selected = Array.from(files || []);
    const invalid = selected.find((file) => !file.type.startsWith("audio/"));
    if (invalid) {
      setError("Only audio files can be attached as evidence.");
      return;
    }

    setError("");
    setAudioFiles((current) => [...current, ...selected]);
  }

  function handleNext() {
    const evidence = audioFiles.map((file) => ({
      name: file.name,
      type: file.type,
      size: file.size,
    }));
    sessionStorage.setItem("audioEvidence", JSON.stringify(evidence));
    navigate("/target-word");
  }

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <Header />
      <ProgressBar currentStep={1} />
      <main className="flex-1 flex items-center justify-center px-4 pb-10">
        <section className="max-w-3xl w-full bg-white rounded-lg shadow p-8 flex flex-col gap-6">
          <div className="flex items-center gap-4">
            <img src={Audio} alt="" className="w-8 h-8" />
            <div>
              <h1 className="text-2xl font-semibold text-gray-900">
                Attach Speech Evidence
              </h1>
              <p className="text-gray-600">
                Audio is optional in this MVP. Use it as source evidence, then enter the
                observed IPA pronunciation variants on the next screen.
              </p>
            </div>
          </div>

          <div
            className="border-2 border-dashed border-indigo-300 rounded-lg p-8 text-center bg-indigo-50"
            onDrop={(event) => {
              event.preventDefault();
              acceptFiles(event.dataTransfer.files);
            }}
            onDragOver={(event) => event.preventDefault()}
          >
            <p className="text-gray-700 font-medium">Drag audio files here</p>
            <p className="text-sm text-gray-500 mt-1">or browse from your computer</p>
            <button
              type="button"
              className="mt-4 bg-indigo-600 text-white hover:bg-indigo-700"
              onClick={() => fileInputRef.current.click()}
            >
              Browse Files
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="audio/*"
              multiple
              className="hidden"
              onChange={(event) => acceptFiles(event.target.files)}
            />
          </div>

          {audioFiles.length > 0 && (
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <div className="px-4 py-3 bg-gray-50 text-sm font-semibold text-gray-700">
                Attached evidence
              </div>
              {audioFiles.map((file, index) => (
                <div
                  key={`${file.name}-${index}`}
                  className="px-4 py-3 flex items-center justify-between border-t border-gray-200"
                >
                  <div>
                    <p className="text-gray-900 font-medium">{file.name}</p>
                    <p className="text-sm text-gray-500">{formatFileSize(file.size)}</p>
                  </div>
                  <button
                    type="button"
                    className="text-red-600 bg-transparent hover:bg-red-50"
                    onClick={() =>
                      setAudioFiles((current) =>
                        current.filter((_, fileIndex) => fileIndex !== index)
                      )
                    }
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="flex items-center justify-between">
            <button
              type="button"
              className="bg-white text-gray-700 border border-gray-300 hover:bg-gray-50"
              onClick={() => {
                sessionStorage.setItem("audioEvidence", "[]");
                navigate("/target-word");
              }}
            >
              Skip Audio
            </button>
            <button
              type="button"
              className="bg-indigo-600 text-white hover:bg-indigo-700"
              onClick={handleNext}
            >
              Continue
            </button>
          </div>

          {error && <p className="text-sm text-red-600 text-right">{error}</p>}
        </section>
      </main>
      <Footer />
    </div>
  );
}
