import React, { useState, useRef } from "react";
import { Upload, Send, Loader2, CheckCircle } from "lucide-react";

const CsvUploadAndPreview = ({
  onDataProcessed,          // parent receives preview / backend result
  isProcessing,             // parent controls spinner state
  onStartProcessing,        // parent sets isProcessing = true
  onStopProcessing,         // parent sets isProcessing = false
  isFileUploaded,           // parent knows upload is successful
  onUploadSuccess,          // parent sets isFileUploaded = true
  headerRowIndex,
  setHeaderRowIndex,
  dataPreview,
}) => {
  const [file, setFile] = useState(null);
  const [hasHeader, setHasHeader] = useState("yes");
  const [showModal, setShowModal] = useState(false);
  const inputRef = useRef(null);

  const parseCSV = (text) => {
    return text
      .split(/\r?\n/)
      .map((line) => line.split(",").map((cell) => cell.trim()))
      .filter((row) => row.length > 0);
  };

  // -----------------------
  // CSV upload + local preview
  // -----------------------
  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];

    if (!selectedFile || !selectedFile.name.endsWith(".csv")) {
      console.error("Please select a valid CSV file.");
      return;
    }

    setFile(selectedFile);

    const reader = new FileReader();
    reader.onload = (evt) => {
      const rows = parseCSV(evt.target.result);
      onDataProcessed(rows);      // send preview to parent
      setShowModal(true);         // show preview modal

      if (typeof onUploadSuccess === "function") {
        onUploadSuccess();        // SET isFileUploaded = true
      }
    };
    reader.readAsText(selectedFile);
  };

  // -----------------------
  // Header selection
  // -----------------------
  const handleHeaderChange = (e) => {
    const value = e.target.value;
    setHasHeader(value);
    setHeaderRowIndex(value === "yes" ? 0 : 1);
  };

  // -----------------------
  // Backend preprocess call
  // -----------------------
  const handlePreprocess = async () => {
    if (!file) {
      console.error("Please upload a CSV first.");
      return;
    }

    onStartProcessing?.(); // enable spinner

    const formData = new FormData();
    formData.append("file", file);
    formData.append("hasHeader", hasHeader);
    formData.append("headerRowIndex", headerRowIndex);

    try {
      const res = await fetch(
        "https://chatcsv-production-c7d2.up.railway.app/upload",
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await res.json();

      if (data.status === "ready") {
        onDataProcessed({
          session_id: data.session_id,
          preview: data.summary.dqr_preview
            ? [data.summary.dqr_preview.split(",")]
            : [],
        });

        console.log("CSV preprocessing done!");
        setShowModal(false);
      } else {
        console.error("Preprocessing failed.");
      }
    } catch (err) {
      console.error("Preprocess error:", err);
    } finally {
      onStopProcessing?.(); // disable spinner
    }
  };

  const headerOptions = (dataPreview || [])
    .slice(0, 5)
    .map((_, index) => (
      <option key={index} value={index}>
        Row {index + 1} (Index {index})
      </option>
    ));

  const maxCols = dataPreview?.reduce(
    (max, row) => Math.max(max, row.length),
    0
  );

  return (
    <div className="p-6 bg-white dark:bg-gray-800 rounded-xl shadow-2xl">
      <h2 className="text-2xl font-extrabold text-indigo-600 mb-4 flex items-center">
        <Upload className="w-6 h-6 mr-2" /> 1. Upload CSV
      </h2>

      {/* Upload area */}
      <div
        className="border-2 border-dashed p-6 rounded-lg text-center cursor-pointer hover:border-indigo-500"
        onClick={() => inputRef.current.click()}
      >
        <input
          type="file"
          accept=".csv"
          onChange={handleFileChange}
          className="hidden"
          ref={inputRef}
        />

        <Upload className="mx-auto h-12 w-12 text-gray-400" />
        <p className="mt-1 text-sm text-gray-600">
          Drag & drop CSV here or click to select.
        </p>

        {file && (
          <p className="mt-2 text-indigo-500 font-medium">{file.name}</p>
        )}

        {/* ✔ Show success indicator */}
        {isFileUploaded && (
          <div className="mt-3 flex items-center justify-center text-green-600 font-semibold">
            <CheckCircle className="w-5 h-5 mr-1" />
            File uploaded successfully
          </div>
        )}
      </div>

      {/* Modal preview */}
      {showModal && dataPreview?.length > 0 && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-[95%] max-w-4xl p-6 relative">
            <button
              onClick={() => setShowModal(false)}
              className="absolute top-3 right-3 text-gray-400 hover:text-red-500 transition cursor-pointer"
            >
              ✕
            </button>

            <h3 className="text-xl font-semibold text-indigo-600 dark:text-indigo-400 mb-3">
              CSV Preview
            </h3>

            <p className="text-sm text-red-500 mb-3">
              ⚠️ Make sure to correctly select the header row — it affects AI
              interpretation.
            </p>

            {/* Header configuration */}
            <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Header Row Configuration
              </label>

              <div className="flex flex-col sm:flex-row sm:space-x-4 mb-3">
                <label className="inline-flex items-center mb-2 sm:mb-0">
                  <input
                    type="radio"
                    name="hasHeader"
                    value="yes"
                    checked={hasHeader === "yes"}
                    onChange={handleHeaderChange}
                    className="form-radio text-indigo-600"
                  />
                  <span className="ml-2 text-gray-700 dark:text-gray-300">
                    Header is at 1st row (Index 0)
                  </span>
                </label>

                <label className="inline-flex items-center">
                  <input
                    type="radio"
                    name="hasHeader"
                    value="no"
                    checked={hasHeader === "no"}
                    onChange={handleHeaderChange}
                    className="form-radio text-indigo-600"
                  />
                  <span className="ml-2 text-gray-700 dark:text-gray-300">
                    No, specify row number
                  </span>
                </label>
              </div>

              {hasHeader === "no" && (
                <div className="w-full sm:w-1/2">
                  <label
                    htmlFor="header-row"
                    className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1"
                  >
                    Header Row Index
                  </label>
                  <select
                    id="header-row"
                    value={headerRowIndex}
                    onChange={(e) =>
                      setHeaderRowIndex(parseInt(e.target.value, 10))
                    }
                    className="block w-full py-2 border rounded-md dark:bg-gray-800 dark:border-gray-600"
                  >
                    {headerOptions}
                  </select>
                </div>
              )}
            </div>

            {/* CSV Table Preview */}
            <div className="overflow-x-auto max-h-[60vh] rounded-lg border border-gray-200 dark:border-gray-700">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-indigo-100 dark:bg-indigo-900/50">
                  <tr>
                    {Array.from({ length: maxCols }).map((_, colIndex) => (
                      <th
                        key={colIndex}
                        className="px-6 py-3 text-left text-xs font-medium text-indigo-700 dark:text-indigo-300 uppercase tracking-wider"
                      >
                        {dataPreview[headerRowIndex]?.[colIndex] ||
                          `Col ${colIndex + 1}`}
                      </th>
                    ))}
                  </tr>
                </thead>

                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {dataPreview
                    .filter((_, i) => i !== headerRowIndex)
                    .slice(0, 5)
                    .map((row, rowIndex) => (
                      <tr key={rowIndex} className="hover:bg-gray-50">
                        {row.map((cell, cellIndex) => (
                          <td
                            key={cellIndex}
                            className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400"
                          >
                            {cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>

            {/* Preprocess Button */}
            <div className="mt-4 flex justify-end">
              <button
                onClick={handlePreprocess}
                disabled={isProcessing}
                className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
              >
                {isProcessing ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
                {isProcessing ? "Processing..." : "Preprocess CSV"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CsvUploadAndPreview;
