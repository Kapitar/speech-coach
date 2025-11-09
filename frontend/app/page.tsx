'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { analyzeVideo, type AnalysisResponse } from '@/lib/api';

export default function Home() {
  const router = useRouter();
  const [isDragging, setIsDragging] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordedVideo, setRecordedVideo] = useState<string | null>(null);
  const [uploadedVideo, setUploadedVideo] = useState<string | null>(null);
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [context, setContext] = useState('');
  const [audience, setAudience] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileSizeWarning, setFileSizeWarning] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    const videoFile = files.find(file => file.type.startsWith('video/'));
    
    if (videoFile) {
      handleVideoFile(videoFile);
    }
  }, []);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type.startsWith('video/')) {
      handleVideoFile(file);
    }
  }, []);

  const handleVideoFile = (file: File) => {
    // Check file size limit for ideal speech generation (11MB)
    const MAX_FILE_SIZE = 11 * 1024 * 1024; // 11MB in bytes
    if (file.size > MAX_FILE_SIZE) {
      const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
      setFileSizeWarning(`Warning: Your video file (${fileSizeMB} MB) exceeds 11 MB. Video analysis will work, but the "Generate Ideal Speech" feature requires files under 11 MB.`);
    } else {
      setFileSizeWarning(null);
    }
    
    const url = URL.createObjectURL(file);
    setUploadedVideo(url);
    setRecordedVideo(null);
    setVideoFile(file);
    localStorage.setItem('uploadedVideo', url);
    localStorage.removeItem('recordedVideo');
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: true, 
        audio: true 
      });
      
      streamRef.current = stream;
      setIsRecording(true);

      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play().catch(err => {
            console.error('Error playing video:', err);
          });
        }
      }, 0);

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'video/webm' });
        const url = URL.createObjectURL(blob);
        const file = new File([blob], 'recorded-video.webm', { type: 'video/webm' });
        
        // Check file size limit for ideal speech generation (11MB)
        const MAX_FILE_SIZE = 11 * 1024 * 1024; // 11MB in bytes
        if (file.size > MAX_FILE_SIZE) {
          const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
          setFileSizeWarning(`Warning: Your recorded video (${fileSizeMB} MB) exceeds 11 MB. Video analysis will work, but the "Generate Ideal Speech" feature requires files under 11 MB.`);
        } else {
          setFileSizeWarning(null);
        }
        
        setRecordedVideo(url);
        setUploadedVideo(null);
        setVideoFile(file);
        localStorage.setItem('recordedVideo', url);
        localStorage.removeItem('uploadedVideo');
        
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
          streamRef.current = null;
        }
        if (videoRef.current) {
          videoRef.current.srcObject = null;
        }
      };

      mediaRecorder.start();
    } catch (error) {
      console.error('Error accessing camera:', error);
      alert('Unable to access camera. Please check permissions.');
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  useEffect(() => {
    if (isRecording && streamRef.current && videoRef.current) {
      videoRef.current.srcObject = streamRef.current;
      videoRef.current.play().catch(err => {
        console.error('Error playing video:', err);
      });
    }
  }, [isRecording]);

  const resetVideo = () => {
    setUploadedVideo(null);
    setRecordedVideo(null);
    setVideoFile(null);
    setContext('');
    setAudience('');
    setError(null);
    localStorage.removeItem('recordedVideo');
    localStorage.removeItem('uploadedVideo');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSubmit = async () => {
    if (!videoFile) {
      setError('Please upload or record a video first');
      return;
    }

    setIsSubmitting(true);
    setIsAnalyzing(true);
    setError(null);

    try {
      // Store video URL for the analysis page
      const videoUrl = uploadedVideo || recordedVideo;
      if (videoUrl) {
        localStorage.setItem('currentVideoUrl', videoUrl);
      }

      // Store the video file as a blob URL for the analysis page to use
      const videoBlobUrl = URL.createObjectURL(videoFile);
      localStorage.setItem('currentVideoFileUrl', videoBlobUrl);
      
      // Also store the file name and type for reference
      localStorage.setItem('currentVideoFileName', videoFile.name);
      localStorage.setItem('currentVideoFileType', videoFile.type);

      // Submit video for analysis
      const feedback = await analyzeVideo(videoFile);
      
      // Store feedback in localStorage for the analysis page
      localStorage.setItem('analysisFeedback', JSON.stringify(feedback));
      
      // Navigate to analysis page
      router.push('/analysis');
    } catch (err) {
      console.error('Error submitting video:', err);
      setError(err instanceof Error ? err.message : 'Failed to analyze video. Please try again.');
      setIsSubmitting(false);
      setIsAnalyzing(false);
    }
  };

  const currentVideo = uploadedVideo || recordedVideo;

  // Show full-screen loader when analyzing
  if (isAnalyzing) {
    return (
      <div className="min-h-screen relative text-white flex items-center justify-center p-6 overflow-hidden">
        <div className="fixed inset-0 static-gradient"></div>
        <div className="fixed top-0 left-1/4 w-[500px] h-[500px] bg-purple-950/8 rounded-full blur-3xl"></div>
        <div className="fixed bottom-0 right-1/4 w-[500px] h-[500px] bg-blue-950/8 rounded-full blur-3xl"></div>
        <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-purple-600/20 rounded-full blur-3xl"></div>
        <div className="relative z-10 text-center max-w-2xl">
          <div className="relative w-24 h-24 mx-auto mb-8">
            <div className="absolute inset-0 border-4 border-white/10 rounded-full"></div>
            <div className="absolute inset-0 border-4 border-transparent border-t-white rounded-full animate-spin"></div>
            <div className="absolute inset-0 border-4 border-transparent border-r-white/50 rounded-full animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }}></div>
          </div>
          <h2 className="text-3xl font-light mb-4 text-white/95">Analyzing Your Speech</h2>
          <p className="text-white/60 text-lg font-light mb-8">
            Our AI is reviewing your video and generating comprehensive feedback...
          </p>
          <div className="space-y-2 text-white/40 text-sm">
            <div className="flex items-center justify-center gap-2">
              <div className="w-1.5 h-1.5 bg-white/40 rounded-full animate-pulse"></div>
              <span>Analyzing non-verbal communication</span>
            </div>
            <div className="flex items-center justify-center gap-2">
              <div className="w-1.5 h-1.5 bg-white/40 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
              <span>Evaluating delivery and clarity</span>
            </div>
            <div className="flex items-center justify-center gap-2">
              <div className="w-1.5 h-1.5 bg-white/40 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
              <span>Assessing content and structure</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative text-white flex items-center justify-center p-6 overflow-hidden">
      {/* Static dark gradient background */}
      <div className="fixed inset-0 static-gradient"></div>
      
      {/* Static subtle orbs for depth */}
      <div className="fixed top-0 left-1/4 w-[500px] h-[500px] bg-purple-950/8 rounded-full blur-3xl"></div>
      <div className="fixed bottom-0 right-1/4 w-[500px] h-[500px] bg-blue-950/8 rounded-full blur-3xl"></div>
      {/* Colored orb in the middle */}
      <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-purple-600/20 rounded-full blur-3xl"></div>
      <div className="fixed top-1/3 right-1/3 w-[300px] h-[300px] bg-purple-950/5 rounded-full blur-3xl"></div>
      
      <div className="relative z-10 w-full max-w-6xl">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-5xl font-light mb-4 tracking-tight text-white/95">
            Speech Coach
          </h1>
          <p className="text-gray-400 text-xl font-light">
            Upload a speech video and get instant feedback
          </p>
        </div>

        {!currentVideo ? (
          <div className="space-y-8">
            {isRecording ? (
              <>
                {/* Live Video Preview */}
                <div className="flex justify-center">
                  <div className="relative rounded-2xl overflow-hidden bg-gray-900/50 backdrop-blur-xl aspect-video w-full max-w-md shadow-2xl border border-white/10">
                    <video
                      ref={videoRef}
                      autoPlay
                      muted
                      playsInline
                      className="w-full h-full object-cover"
                    />
                    {/* Recording indicator */}
                    <div className="absolute top-5 left-5 flex items-center gap-2.5 bg-black/70 backdrop-blur-md px-4 py-2 rounded-full border border-white/10">
                      <span className="w-2.5 h-2.5 bg-red-500 rounded-full animate-pulse shadow-lg shadow-red-500/50"></span>
                      <span className="text-sm text-white font-medium">Recording</span>
                    </div>
                  </div>
                </div>
                {/* Stop Recording Button */}
                <div className="text-center">
                  <button
                    onClick={stopRecording}
                    className="px-10 py-3.5 rounded-full font-medium transition-all duration-300 bg-red-500 hover:bg-red-600 text-white cursor-pointer shadow-lg shadow-red-500/30 hover:shadow-xl hover:shadow-red-500/40 hover:scale-105 active:scale-95"
                  >
                    <span className="flex items-center gap-2.5 justify-center">
                      <span className="w-2 h-2 bg-white rounded-full animate-pulse"></span>
                      Stop Recording
                    </span>
                  </button>
                </div>
              </>
            ) : (
              <>
                {/* Upload Area */}
                <div
                  className={`relative rounded-3xl transition-all duration-500 ${
                    isDragging
                      ? 'bg-white/5 border-2 border-white/30 shadow-2xl scale-[1.02]'
                      : 'bg-white/5 backdrop-blur-xl border-2 border-white/10 hover:border-white/20 hover:bg-white/[0.07]'
                  }`}
                  onDragEnter={handleDragEnter}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                >
                  <div className="p-20 text-center">
                    <div className="w-20 h-20 mx-auto mb-8 rounded-full bg-white/10 flex items-center justify-center backdrop-blur-sm border border-white/20">
                      <svg
                        className="w-10 h-10 text-white/70"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={1.5}
                          d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                        />
                      </svg>
                    </div>
                    <p className="text-white/90 mb-2 text-xl font-light">
                      Drop your video here
                    </p>
                    <p className="text-white/40 text-sm mb-8 font-light">or</p>
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="px-8 py-3 rounded-full bg-white text-black hover:bg-white/90 transition-all duration-300 text-sm font-medium cursor-pointer shadow-lg hover:shadow-xl hover:scale-105 active:scale-95"
                    >
                      Browse Files
                    </button>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="video/*"
                      onChange={handleFileInput}
                      className="hidden"
                    />
                  </div>
                </div>

                {/* Divider */}
                <div className="flex items-center gap-6">
                  <div className="flex-1 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>
                  <span className="text-white/40 text-sm font-light">or</span>
                  <div className="flex-1 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>
                </div>

                {/* Record Button */}
                <div className="text-center">
                  <button
                    onClick={startRecording}
                    className="px-10 py-3.5 rounded-full font-medium transition-all duration-300 bg-white/10 hover:bg-white/15 text-white border border-white/20 hover:border-white/30 cursor-pointer backdrop-blur-sm hover:scale-105 active:scale-95 shadow-lg hover:shadow-xl"
                  >
                    Record Video
                  </button>
                </div>
              </>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10 items-start">
            {/* Left Side - Video */}
            <div className="flex flex-col items-center md:items-start">
              <div className="relative rounded-2xl overflow-hidden bg-gray-900/50 backdrop-blur-xl w-full max-w-sm shadow-2xl border border-white/10">
                <video
                  src={currentVideo}
                  controls
                  className="w-full h-auto"
                />
              </div>
            </div>
            
            {/* Right Side - Form Fields */}
            <div className="space-y-6">
              <div className="space-y-5">
                <div>
                  <label htmlFor="context" className="block text-sm text-white/70 mb-3 font-medium">
                    Context <span className="text-white/40 font-normal">(optional)</span>
                  </label>
                  <input
                    id="context"
                    type="text"
                    value={context}
                    onChange={(e) => setContext(e.target.value)}
                    placeholder="e.g., Job interview, presentation to investors..."
                    className="w-full px-5 py-3.5 bg-white/5 backdrop-blur-xl border border-white/10 rounded-xl text-white placeholder-white/30 focus:outline-none focus:border-white/30 focus:bg-white/10 transition-all duration-300"
                  />
                </div>
                
                <div>
                  <label htmlFor="audience" className="block text-sm text-white/70 mb-3 font-medium">
                    Audience <span className="text-white/40 font-normal">(optional)</span>
                  </label>
                  <input
                    id="audience"
                    type="text"
                    value={audience}
                    onChange={(e) => setAudience(e.target.value)}
                    placeholder="e.g., Hiring managers, potential clients..."
                    className="w-full px-5 py-3.5 bg-white/5 backdrop-blur-xl border border-white/10 rounded-xl text-white placeholder-white/30 focus:outline-none focus:border-white/30 focus:bg-white/10 transition-all duration-300"
                  />
                </div>
              </div>

              {/* File Size Warning */}
              {fileSizeWarning && (
                <div className="px-4 py-3 bg-yellow-500/10 border border-yellow-500/30 rounded-xl">
                  <div className="flex items-start gap-3">
                    <svg className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    <div className="flex-1">
                      <p className="text-yellow-300 text-sm leading-relaxed">{fileSizeWarning}</p>
                    </div>
                    <button
                      onClick={() => setFileSizeWarning(null)}
                      className="text-yellow-400 hover:text-yellow-300 transition-colors flex-shrink-0"
                    >
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                    </button>
                  </div>
                </div>
              )}

              {/* Error Message */}
              {error && (
                <div className="px-4 py-3 bg-red-500/20 border border-red-500/30 rounded-xl text-red-300 text-sm">
                  {error}
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-4 pt-2">
                <button
                  onClick={resetVideo}
                  disabled={isSubmitting}
                  className="flex-1 px-6 py-3.5 bg-white/5 hover:bg-white/10 text-white rounded-xl transition-all duration-300 border border-white/10 hover:border-white/20 cursor-pointer backdrop-blur-sm font-medium hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                >
                  Upload Another
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={isSubmitting || !videoFile}
                  className="flex-1 px-8 py-3.5 bg-white hover:bg-white/90 text-black rounded-xl transition-all duration-300 font-medium cursor-pointer shadow-lg hover:shadow-xl hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center justify-center gap-2"
                >
                  {isSubmitting ? (
                    <>
                      <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Analyzing...
                    </>
                  ) : (
                    'Submit'
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
