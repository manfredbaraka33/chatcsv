import { useState } from 'react';
import './App.css';
import CsvUploadAndPreview from './components/CsvUploadAndPreview';
import QuestionBox from './components/QuestionBox';

function App() {
  const [dataPreview, setDataPreview] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [headerRowIndex, setHeaderRowIndex] = useState(0);
  const [isFileUploaded, setIsFileUploaded] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [sessionId, setSessionId] = useState(null); 

  const handleDataProcessed = (processedData) => {
    if (processedData && processedData.session_id) {
      setDataPreview(processedData.preview || []);
      setIsFileUploaded(true);
      setSessionId(processedData.session_id); 
    } else {
      setDataPreview(processedData || []);
      setIsFileUploaded(false);
      setSessionId(null);
    }
  };

  return (
    <div className='min-h-screen pt-4 px-2 bg-linear-to-br from-indigo-50 via-white to-indigo-100 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900'>
      <center>
        <h1 className='text-gray-500 text-3xl sm:text-4xl font-extrabold text-center bg-clip-text'>
          CSV Intelligence Dashboard
        </h1>
      </center>

      <div className="flex flex-col lg:flex-row items-start justify-start p-2 sm:p-6 space-y-4 lg:space-y-0 lg:space-x-6">

        <div className="flex-1 w-full">
          {/* <CsvUploadAndPreview
            onDataProcessed={handleDataProcessed}
            isProcessing={isProcessing}
            dataPreview={dataPreview}
            headerRowIndex={headerRowIndex}
            setHeaderRowIndex={setHeaderRowIndex}
            isFileUploaded={isFileUploaded}
          /> */}

          <CsvUploadAndPreview
            onDataProcessed={handleDataProcessed}
            isProcessing={isProcessing}
            dataPreview={dataPreview}
          
            headerRowIndex={headerRowIndex}
            setHeaderRowIndex={setHeaderRowIndex}
          
            isFileUploaded={isFileUploaded}

            onStartProcessing={() => setIsProcessing(true)}
            onStopProcessing={() => setIsProcessing(false)}
          />

        </div>

        <div className="flex-1 w-full">
          <QuestionBox
            isEnabled={!!sessionId}        
            chatHistory={chatHistory}
            setChatHistory={setChatHistory}
            sessionId={sessionId}           
          />
        </div>

      </div>
    </div>
  );
}

export default App;
