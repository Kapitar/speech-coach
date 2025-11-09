'use client';

import { useState, useEffect, useRef, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import {
  type FeedbackResponse,
  calculateSectionScore,
  parseTimeRange,
  startChat,
  sendChatMessage,
  generateIdealSpeech,
} from '@/lib/api';

function AnalysisContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<FeedbackResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'replay' | 'chat'>('replay');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([]);
  const [chatInput, setChatInput] = useState('');
  const [isSendingChat, setIsSendingChat] = useState(false);
  const [isGeneratingSpeech, setIsGeneratingSpeech] = useState(false);
  const [fileSizeError, setFileSizeError] = useState<string | null>(null);
  const [idealSpeechData, setIdealSpeechData] = useState<{
    audioUrl: string;
    originalTranscription: string;
    improvedSpeech: string;
    suggestions: string[];
    keyChanges: Array<{ change: string; reason: string }>;
    summary: string;
  } | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Load video URL
    const urlParam = searchParams.get('video');
    const storedVideo = localStorage.getItem('currentVideoUrl') || 
                       localStorage.getItem('recordedVideo') || 
                       localStorage.getItem('uploadedVideo');
    
    if (urlParam) {
      setVideoUrl(urlParam);
    } else if (storedVideo) {
      setVideoUrl(storedVideo);
    }

    // Load feedback
    const storedFeedback = localStorage.getItem('analysisFeedback');
    if (storedFeedback) {
      try {
        const parsed = JSON.parse(storedFeedback) as FeedbackResponse;
        setFeedback(parsed);
      } catch (err) {
        setError('Failed to load analysis feedback');
      }
    } else {
      setError('No analysis feedback found. Please submit a video first.');
    }
    setLoading(false);
  }, [searchParams]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const [isInitializingChat, setIsInitializingChat] = useState(false);

  // Initialize chat when feedback is loaded
  useEffect(() => {
    if (feedback && !conversationId && !isInitializingChat) {
      setIsInitializingChat(true);
      startChat(feedback)
        .then((response) => {
          setConversationId(response.conversation_id);
          setChatMessages([{
            role: 'assistant',
            content: response.message,
          }]);
        })
        .catch((err) => {
          console.error('Failed to start chat:', err);
        })
        .finally(() => {
          setIsInitializingChat(false);
        });
    }
  }, [feedback, conversationId, isInitializingChat]);

  const handleSendChatMessage = async () => {
    if (!chatInput.trim() || !conversationId || isSendingChat) return;

    const userMessage = chatInput.trim();
    setChatInput('');
    setIsSendingChat(true);
    setChatMessages((prev) => [...prev, { role: 'user', content: userMessage }]);

    try {
      const response = await sendChatMessage(conversationId, userMessage);
      setChatMessages((prev) => [...prev, { role: 'assistant', content: response.assistant_reply }]);
    } catch (err) {
      setChatMessages((prev) => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
      }]);
    } finally {
      setIsSendingChat(false);
    }
  };

  const handleGenerateIdealSpeech = async () => {
    if (!videoUrl || isGeneratingSpeech) return;

    setIsGeneratingSpeech(true);
    setFileSizeError(null);
    
    try {
      // Get the original video file from localStorage blob URL
      const videoFileUrl = localStorage.getItem('currentVideoFileUrl') || videoUrl;
      const videoFileName = localStorage.getItem('currentVideoFileName') || 'video.mp4';
      const videoFileType = localStorage.getItem('currentVideoFileType') || 'video/mp4';
      
      // Fetch the video file as a blob
      const response = await fetch(videoFileUrl);
      if (!response.ok) {
        throw new Error('Failed to fetch video file');
      }
      
      const videoBlob = await response.blob();
      
      if (videoBlob.size === 0) {
        throw new Error('Video file is empty');
      }
      
      // Check file size limit (11MB = 11 * 1024 * 1024 bytes)
      const MAX_FILE_SIZE = 11 * 1024 * 1024; // 11MB in bytes
      if (videoBlob.size > MAX_FILE_SIZE) {
        const fileSizeMB = (videoBlob.size / (1024 * 1024)).toFixed(2);
        setFileSizeError(`File size (${fileSizeMB} MB) exceeds the maximum limit of 11 MB. Please use a smaller video file.`);
        setIsGeneratingSpeech(false);
        return;
      }
      
      // Create a File object from the blob with the original filename
      // The backend endpoint accepts audio files, but video files with audio tracks should work too
      const videoFile = new File([videoBlob], videoFileName, { type: videoFileType });
      
      console.log(`Sending video file to backend: ${videoFile.size} bytes, type: ${videoFileType}, name: ${videoFileName}`);
      
      // Call backend endpoint directly with the video file
      // The backend should be able to extract audio from the video file
      const result = await generateIdealSpeech(videoFile);
      
      setIdealSpeechData({
        audioUrl: result.audioUrl,
        originalTranscription: result.original_transcription,
        improvedSpeech: result.improved_content.improved_speech,
        suggestions: result.improved_content.suggestions,
        keyChanges: result.improved_content.key_changes,
        summary: result.improved_content.summary,
      });
    } catch (err) {
      console.error('Failed to generate ideal speech:', err);
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setFileSizeError(`Failed to generate ideal speech: ${errorMessage}\n\nPlease ensure:\n- Your video has an audio track\n- The video file is not corrupted\n- Try uploading the video again`);
    } finally {
      setIsGeneratingSpeech(false);
    }
  };

  // Calculate overall score
  const calculateOverallScore = (): number => {
    if (!feedback) return 0;
    
    const nonVerbalScore = calculateSectionScore([
      feedback.non_verbal.eye_contact,
      feedback.non_verbal.gestures,
      feedback.non_verbal.posture,
    ]);
    
    const deliveryScore = calculateSectionScore([
      feedback.delivery.clarity_enunciation,
      feedback.delivery.intonation,
      feedback.delivery.eloquence_filler_words,
    ]);
    
    const contentScore = calculateSectionScore([
      feedback.content.organization_flow,
      feedback.content.persuasiveness_impact,
      feedback.content.clarity_of_message,
    ]);
    
    return Math.round((nonVerbalScore + deliveryScore + contentScore) / 3);
  };

  // Get all timestamped feedback
  const getAllTimestampedFeedback = () => {
    if (!feedback) return [];
    
    const allFeedback: Array<{
      timeRange: string;
      category: string;
      subCategory: string;
      details: string[];
    }> = [];

    // Non-verbal feedback
    Object.entries(feedback.non_verbal).forEach(([key, value]) => {
      value.timestamped_feedback.forEach((tf) => {
        if (tf.time_range && tf.time_range.trim() !== '') {
          allFeedback.push({
            timeRange: tf.time_range,
            category: 'Non-Verbal',
            subCategory: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
            details: tf.details,
          });
        }
      });
    });

    // Delivery feedback
    Object.entries(feedback.delivery).forEach(([key, value]) => {
      value.timestamped_feedback.forEach((tf) => {
        if (tf.time_range && tf.time_range.trim() !== '') {
          allFeedback.push({
            timeRange: tf.time_range,
            category: 'Delivery',
            subCategory: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
            details: tf.details,
          });
        }
      });
    });

    // Content feedback
    Object.entries(feedback.content).forEach(([key, value]) => {
      value.timestamped_feedback.forEach((tf) => {
        if (tf.time_range && tf.time_range.trim() !== '') {
          allFeedback.push({
            timeRange: tf.time_range,
            category: 'Content',
            subCategory: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
            details: tf.details,
          });
        }
      });
    });

    // Debug: log time ranges to see what we're getting
    if (allFeedback.length > 0) {
      console.log('Timestamped feedback time ranges:', allFeedback.map(f => f.timeRange));
    }

    return allFeedback.sort((a, b) => {
      const aStart = parseTimeRange(a.timeRange).start;
      const bStart = parseTimeRange(b.timeRange).start;
      return aStart - bStart;
    });
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-400';
    if (score >= 60) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getScoreBgColor = (score: number) => {
    if (score >= 80) return 'bg-green-500/20 border-green-500/30';
    if (score >= 60) return 'bg-yellow-500/20 border-yellow-500/30';
    return 'bg-red-500/20 border-red-500/30';
  };

  // Get category color for timestamps
  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'Non-Verbal':
        return {
          bg: 'bg-purple-500/20',
          border: 'border-purple-500/30',
          text: 'text-purple-300',
          circleBg: 'bg-purple-500/20',
          circleBorder: 'border-purple-500/30',
        };
      case 'Delivery':
        return {
          bg: 'bg-blue-500/20',
          border: 'border-blue-500/30',
          text: 'text-blue-300',
          circleBg: 'bg-blue-500/20',
          circleBorder: 'border-blue-500/30',
        };
      case 'Content':
        return {
          bg: 'bg-green-500/20',
          border: 'border-green-500/30',
          text: 'text-green-300',
          circleBg: 'bg-green-500/20',
          circleBorder: 'border-green-500/30',
        };
      default:
        return {
          bg: 'bg-gray-500/20',
          border: 'border-gray-500/30',
          text: 'text-gray-300',
          circleBg: 'bg-gray-500/20',
          circleBorder: 'border-gray-500/30',
        };
    }
  };

  // Circular progress component
  const CircularProgress = ({ score, size = 120, strokeWidth = 8 }: { score: number; size?: number; strokeWidth?: number }) => {
    const radius = (size - strokeWidth) / 2;
    const circumference = radius * 2 * Math.PI;
    const offset = circumference - (score / 100) * circumference;
    const color = score >= 80 ? '#22c55e' : score >= 60 ? '#eab308' : '#ef4444';
    
    return (
      <div className="relative" style={{ width: size, height: size }}>
        <svg className="transform -rotate-90" width={size} height={size}>
          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="rgba(255, 255, 255, 0.08)"
            strokeWidth={strokeWidth}
            fill="none"
          />
          {/* Progress circle with gradient effect */}
          <defs>
            <linearGradient id={`gradient-${score}`} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={color} stopOpacity="1" />
              <stop offset="100%" stopColor={color} stopOpacity="0.8" />
            </linearGradient>
          </defs>
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={`url(#gradient-${score})`}
            strokeWidth={strokeWidth}
            fill="none"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-all duration-1000 ease-out"
            style={{ 
              filter: `drop-shadow(0 0 12px ${color}50)`,
            }}
          />
        </svg>
      </div>
    );
  };

  // Mini progress bar
  const MiniProgressBar = ({ label, score }: { label: string; score: number }) => {
    const [animatedWidth, setAnimatedWidth] = useState(0);
    const color = score >= 80 ? 'rgb(34, 197, 94)' : score >= 60 ? 'rgb(234, 179, 8)' : 'rgb(239, 68, 68)';

    useEffect(() => {
      const timer = setTimeout(() => {
        setAnimatedWidth(score);
      }, 100);
      return () => clearTimeout(timer);
    }, [score]);

    return (
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <span className="text-xs text-white/70 font-medium">{label}</span>
          <span className="text-xs font-medium" style={{ color }}>{score}%</span>
        </div>
        <div className="h-1.5 bg-white/5 rounded-full overflow-hidden relative">
          <div
            className="h-full rounded-full transition-all duration-700 ease-out"
            style={{
              width: `${animatedWidth}%`,
              backgroundColor: color,
              boxShadow: `0 0 8px ${color}40`,
              minWidth: animatedWidth > 0 ? '2px' : '0',
            }}
          />
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen relative text-white flex items-center justify-center p-6 overflow-hidden">
        <div className="fixed inset-0 static-gradient"></div>
        <div className="fixed top-0 left-1/4 w-[500px] h-[500px] bg-teal-900/12 rounded-full blur-3xl"></div>
        <div className="fixed bottom-0 right-1/4 w-[500px] h-[500px] bg-emerald-900/10 rounded-full blur-3xl"></div>
        <div className="relative z-10 text-center">
          <div className="relative w-20 h-20 mx-auto mb-6">
            <div className="absolute inset-0 border-4 border-white/10 rounded-full"></div>
            <div className="absolute inset-0 border-4 border-transparent border-t-white rounded-full animate-spin"></div>
          </div>
          <p className="text-white/80 text-lg font-light">Loading analysis...</p>
          <p className="text-white/40 text-sm mt-2">Please wait</p>
        </div>
      </div>
    );
  }

  if (error || !feedback) {
    return (
      <div className="min-h-screen relative text-white flex items-center justify-center p-6 overflow-hidden">
        <div className="fixed inset-0 static-gradient"></div>
        <div className="relative z-10 text-center">
          <p className="text-red-400 mb-4">{error || 'No feedback available'}</p>
          <button
            onClick={() => router.push('/')}
            className="px-6 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-white border border-white/20 transition-all duration-300"
          >
            Go Back to Upload
          </button>
        </div>
      </div>
    );
  }

  const overallScore = calculateOverallScore();
  const nonVerbalScore = calculateSectionScore([
    feedback.non_verbal.eye_contact,
    feedback.non_verbal.gestures,
    feedback.non_verbal.posture,
  ]);
  const deliveryScore = calculateSectionScore([
    feedback.delivery.clarity_enunciation,
    feedback.delivery.intonation,
    feedback.delivery.eloquence_filler_words,
  ]);
  const contentScore = calculateSectionScore([
    feedback.content.organization_flow,
    feedback.content.persuasiveness_impact,
    feedback.content.clarity_of_message,
  ]);

  const timestampedFeedback = getAllTimestampedFeedback();

  return (
    <div className="min-h-screen relative text-white p-6 overflow-hidden">
      <div className="fixed inset-0 static-gradient"></div>
      <div className="fixed top-0 left-1/4 w-[500px] h-[500px] bg-teal-900/12 rounded-full blur-3xl"></div>
      <div className="fixed bottom-0 right-1/4 w-[500px] h-[500px] bg-emerald-900/10 rounded-full blur-3xl"></div>
      <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-cyan-600/15 rounded-full blur-3xl"></div>
      <div className="fixed top-1/3 right-1/3 w-[300px] h-[300px] bg-indigo-900/8 rounded-full blur-3xl"></div>
      <div className="fixed bottom-1/4 left-1/3 w-[400px] h-[400px] bg-teal-800/6 rounded-full blur-3xl"></div>
      
      <div className="relative z-10 max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-6">
          <h1 className="text-4xl font-light mb-2 tracking-tight text-white/95">
            Speech Analysis
          </h1>
          <p className="text-gray-400 text-lg font-light">
            Comprehensive feedback and improvement suggestions
          </p>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 justify-center">
          <button
            onClick={() => setActiveTab('replay')}
            className={`px-6 py-2 rounded-xl transition-all duration-300 font-medium ${
              activeTab === 'replay'
                ? 'bg-white text-black'
                : 'bg-white/5 text-white border border-white/10 hover:bg-white/10'
            }`}
          >
            Replay
          </button>
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`px-6 py-2 rounded-xl transition-all duration-300 font-medium ${
              activeTab === 'dashboard'
                ? 'bg-white text-black'
                : 'bg-white/5 text-white border border-white/10 hover:bg-white/10'
            }`}
          >
            Dashboard
          </button>
          <button
            onClick={() => setActiveTab('chat')}
            className={`px-6 py-2 rounded-xl transition-all duration-300 font-medium ${
              activeTab === 'chat'
                ? 'bg-white text-black'
                : 'bg-white/5 text-white border border-white/10 hover:bg-white/10'
            }`}
          >
            Chat
          </button>
        </div>

        {/* Replay Tab */}
        {activeTab === 'replay' && (
          <div className="space-y-4">
            <div className="rounded-xl bg-white/5 backdrop-blur-xl border border-white/10 p-4">
              <h2 className="text-sm text-white/70 mb-3 font-medium uppercase tracking-wide">Video Replay</h2>
              {videoUrl ? (
                <div className="relative rounded-lg overflow-hidden bg-black/20 aspect-video mb-4">
                  <video
                    ref={videoRef}
                    src={videoUrl}
                    controls
                    className="w-full h-full object-contain"
                  />
                </div>
              ) : (
                <div className="relative rounded-lg overflow-hidden bg-black/20 aspect-video flex items-center justify-center border border-white/10 mb-4">
                  <p className="text-white/40 text-sm">No video available</p>
                </div>
              )}

              {/* Timestamped Feedback */}
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {timestampedFeedback.length > 0 ? (
                  timestampedFeedback.map((tf, idx) => {
                    const { start, end } = parseTimeRange(tf.timeRange);
                    const categoryColor = getCategoryColor(tf.category);
                    // Format time as MM:SS
                    const formatTime = (seconds: number): string => {
                      const mins = Math.floor(seconds / 60);
                      const secs = Math.floor(seconds % 60);
                      return `${mins}:${String(secs).padStart(2, '0')}`;
                    };
                    
                    return (
                      <div
                        key={idx}
                        className={`${categoryColor.bg} rounded-lg p-4 border ${categoryColor.border} hover:border-opacity-50 transition-all duration-300 cursor-pointer`}
                        onClick={() => {
                          if (videoRef.current) {
                            videoRef.current.currentTime = start;
                            videoRef.current.play();
                          }
                        }}
                      >
                        <div className="flex items-start gap-3">
                          <div className="flex-shrink-0">
                            <div className={`w-12 h-12 rounded-full ${categoryColor.circleBg} border ${categoryColor.circleBorder} flex items-center justify-center`}>
                              <span className={`${categoryColor.text} font-medium text-xs`}>
                                {formatTime(start)}
                              </span>
                            </div>
                          </div>
                          <div className="flex-1 space-y-2 min-w-0">
                            <div>
                              <div className="text-xs text-white/50 mb-1 font-medium uppercase tracking-wide">
                                {tf.category} - {tf.subCategory}
                              </div>
                              <ul className="space-y-1">
                                {tf.details.map((detail, detailIdx) => (
                                  <li key={detailIdx} className="text-white/80 leading-relaxed font-light text-xs">
                                    • {detail}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <p className="text-white/40 text-sm text-center py-4">No timestamped feedback available</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="space-y-4">
            {/* Overall Score & Feedback Combined */}
            <div className="rounded-2xl bg-white/5 backdrop-blur-xl border border-white/10 p-8 shadow-2xl">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Left Side - Overall Score (Larger & More Prominent) */}
                <div className="lg:col-span-1 flex flex-col items-center justify-center">
                  <div className="relative">
                    <CircularProgress score={overallScore} size={200} strokeWidth={12} />
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <div className={`text-6xl font-light ${getScoreColor(overallScore)} mb-2`}>
                        {overallScore}
                      </div>
                      <div className="text-xs text-white/40 font-medium">/100</div>
                    </div>
                  </div>
                  <div className={`mt-6 text-lg font-medium ${getScoreColor(overallScore)} px-6 py-2 rounded-full bg-white/5 backdrop-blur-sm border border-white/10`}>
                    {overallScore >= 80 ? 'Excellent' : overallScore >= 60 ? 'Good' : 'Needs Improvement'}
                  </div>
                  <p className="mt-4 text-xs text-white/50 font-light uppercase tracking-wider">Overall Score</p>
                  
                  {/* Section Scores */}
                  <div className="mt-8 w-full space-y-3">
                    <div className="flex items-center justify-between px-4 py-2 bg-white/5 rounded-lg border border-white/10">
                      <span className="text-sm text-white/70 font-light">Non-Verbal</span>
                      <span className={`text-lg font-light ${getScoreColor(nonVerbalScore)}`}>{nonVerbalScore}</span>
                    </div>
                    <div className="flex items-center justify-between px-4 py-2 bg-white/5 rounded-lg border border-white/10">
                      <span className="text-sm text-white/70 font-light">Delivery</span>
                      <span className={`text-lg font-light ${getScoreColor(deliveryScore)}`}>{deliveryScore}</span>
                    </div>
                    <div className="flex items-center justify-between px-4 py-2 bg-white/5 rounded-lg border border-white/10">
                      <span className="text-sm text-white/70 font-light">Content</span>
                      <span className={`text-lg font-light ${getScoreColor(contentScore)}`}>{contentScore}</span>
                    </div>
                  </div>
                </div>
                
                {/* Right Side - Overall Feedback (Better Organized) */}
                <div className="lg:col-span-2 flex flex-col justify-center space-y-6">
                  <div>
                    <h2 className="text-2xl font-light mb-1 text-white/95">Overall Feedback</h2>
                    <div className="h-px w-16 bg-gradient-to-r from-white/30 to-transparent mt-2"></div>
                  </div>
                  
                  {/* Summary */}
                  <div className="bg-black/20 rounded-xl p-5 border border-white/5">
                    <h3 className="text-sm text-white/70 mb-3 font-medium uppercase tracking-wide flex items-center gap-2">
                      <div className="w-1 h-4 bg-gradient-to-b from-white/60 to-transparent rounded-full"></div>
                      Summary
                    </h3>
                    <p className="text-white/90 leading-relaxed text-base font-light">{feedback.overall_feedback.summary}</p>
                  </div>
                  
                  {/* Strengths & Areas to Improve */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-green-500/10 rounded-xl p-4 border border-green-500/20">
                      <h3 className="text-sm text-green-300/90 mb-3 font-medium uppercase tracking-wide flex items-center gap-2">
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                        Strengths
                      </h3>
                      <ul className="space-y-2">
                        {feedback.overall_feedback.strengths.map((strength, idx) => (
                          <li key={idx} className="text-white/90 text-sm flex items-start gap-2.5">
                            <span className="text-green-400 mt-1 text-lg leading-none">✓</span>
                            <span className="font-light">{strength}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                    
                    <div className="bg-yellow-500/10 rounded-xl p-4 border border-yellow-500/20">
                      <h3 className="text-sm text-yellow-300/90 mb-3 font-medium uppercase tracking-wide flex items-center gap-2">
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                        Areas to Improve
                      </h3>
                      <ul className="space-y-2">
                        {feedback.overall_feedback.areas_to_improve.map((area, idx) => (
                          <li key={idx} className="text-white/90 text-sm flex items-start gap-2.5">
                            <span className="text-yellow-400 mt-1 text-lg leading-none">→</span>
                            <span className="font-light">{area}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* Prioritized Actions */}
                  <div className="bg-purple-500/10 rounded-xl p-5 border border-purple-500/20">
                    <h3 className="text-sm text-purple-300/90 mb-4 font-medium uppercase tracking-wide flex items-center gap-2">
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                      </svg>
                      Prioritized Actions
                    </h3>
                    <div className="space-y-3">
                      {feedback.overall_feedback.prioritized_actions.map((action, idx) => (
                        <div key={idx} className="flex items-start gap-3 bg-black/20 rounded-lg p-3 border border-white/5">
                          <div className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-500/30 border border-purple-500/50 flex items-center justify-center">
                            <span className="text-purple-300 text-xs font-medium">{idx + 1}</span>
                          </div>
                          <p className="text-white/90 text-sm font-light flex-1 pt-0.5">{action}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Section Scores */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {/* Non-Verbal */}
              <div className="rounded-2xl bg-gradient-to-br from-white/5 to-white/[0.02] backdrop-blur-xl border border-white/10 p-6 shadow-lg hover:shadow-xl transition-all duration-300">
                <div className="flex items-center justify-between mb-5">
                  <h3 className="text-xl font-light text-white/95">Non-Verbal</h3>
                  <div className={`text-3xl font-light ${getScoreColor(nonVerbalScore)}`}>
                    {nonVerbalScore}
                  </div>
                </div>
                <div className="space-y-3 mb-5">
                  <MiniProgressBar label="Eye Contact" score={feedback.non_verbal.eye_contact.effectiveness_score} />
                  <MiniProgressBar label="Gestures" score={feedback.non_verbal.gestures.effectiveness_score} />
                  <MiniProgressBar label="Posture" score={feedback.non_verbal.posture.effectiveness_score} />
                </div>
                {/* Overall Feedback for Non-Verbal Section */}
                <div className="pt-5 border-t border-white/10">
                  <div className="text-xs text-purple-300/80 mb-3 font-medium uppercase tracking-wide flex items-center gap-2">
                    <div className="w-1 h-3 bg-purple-400/60 rounded-full"></div>
                    Overall Feedback
                  </div>
                  <div className="space-y-4 text-sm">
                    <div className="bg-purple-500/5 rounded-lg p-3 border border-purple-500/10">
                      <div className="text-xs text-purple-300/80 mb-1.5 font-medium">Eye Contact</div>
                      <p className="text-white/85 leading-relaxed text-xs">{feedback.non_verbal.eye_contact.overall_feedback}</p>
                    </div>
                    <div className="bg-purple-500/5 rounded-lg p-3 border border-purple-500/10">
                      <div className="text-xs text-purple-300/80 mb-1.5 font-medium">Gestures</div>
                      <p className="text-white/85 leading-relaxed text-xs">{feedback.non_verbal.gestures.overall_feedback}</p>
                    </div>
                    <div className="bg-purple-500/5 rounded-lg p-3 border border-purple-500/10">
                      <div className="text-xs text-purple-300/80 mb-1.5 font-medium">Posture</div>
                      <p className="text-white/85 leading-relaxed text-xs">{feedback.non_verbal.posture.overall_feedback}</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Delivery */}
              <div className="rounded-2xl bg-gradient-to-br from-white/5 to-white/[0.02] backdrop-blur-xl border border-white/10 p-6 shadow-lg hover:shadow-xl transition-all duration-300">
                <div className="flex items-center justify-between mb-5">
                  <h3 className="text-xl font-light text-white/95">Delivery</h3>
                  <div className={`text-3xl font-light ${getScoreColor(deliveryScore)}`}>
                    {deliveryScore}
                  </div>
                </div>
                <div className="space-y-3 mb-5">
                  <MiniProgressBar label="Clarity & Enunciation" score={feedback.delivery.clarity_enunciation.effectiveness_score} />
                  <MiniProgressBar label="Intonation" score={feedback.delivery.intonation.effectiveness_score} />
                  <MiniProgressBar label="Eloquence & Filler Words" score={feedback.delivery.eloquence_filler_words.effectiveness_score} />
                </div>
                {/* Overall Feedback for Delivery Section */}
                <div className="pt-5 border-t border-white/10">
                  <div className="text-xs text-blue-300/80 mb-3 font-medium uppercase tracking-wide flex items-center gap-2">
                    <div className="w-1 h-3 bg-blue-400/60 rounded-full"></div>
                    Overall Feedback
                  </div>
                  <div className="space-y-4 text-sm">
                    <div className="bg-blue-500/5 rounded-lg p-3 border border-blue-500/10">
                      <div className="text-xs text-blue-300/80 mb-1.5 font-medium">Clarity & Enunciation</div>
                      <p className="text-white/85 leading-relaxed text-xs">{feedback.delivery.clarity_enunciation.overall_feedback}</p>
                    </div>
                    <div className="bg-blue-500/5 rounded-lg p-3 border border-blue-500/10">
                      <div className="text-xs text-blue-300/80 mb-1.5 font-medium">Intonation</div>
                      <p className="text-white/85 leading-relaxed text-xs">{feedback.delivery.intonation.overall_feedback}</p>
                    </div>
                    <div className="bg-blue-500/5 rounded-lg p-3 border border-blue-500/10">
                      <div className="text-xs text-blue-300/80 mb-1.5 font-medium">Eloquence & Filler Words</div>
                      <p className="text-white/85 leading-relaxed text-xs">{feedback.delivery.eloquence_filler_words.overall_feedback}</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Content */}
              <div className="rounded-2xl bg-gradient-to-br from-white/5 to-white/[0.02] backdrop-blur-xl border border-white/10 p-6 shadow-lg hover:shadow-xl transition-all duration-300">
                <div className="flex items-center justify-between mb-5">
                  <h3 className="text-xl font-light text-white/95">Content</h3>
                  <div className={`text-3xl font-light ${getScoreColor(contentScore)}`}>
                    {contentScore}
                  </div>
                </div>
                <div className="space-y-3 mb-5">
                  <MiniProgressBar label="Organization & Flow" score={feedback.content.organization_flow.effectiveness_score} />
                  <MiniProgressBar label="Persuasiveness & Impact" score={feedback.content.persuasiveness_impact.effectiveness_score} />
                  <MiniProgressBar label="Clarity of Message" score={feedback.content.clarity_of_message.effectiveness_score} />
                </div>
                {/* Overall Feedback for Content Section */}
                <div className="pt-5 border-t border-white/10">
                  <div className="text-xs text-green-300/80 mb-3 font-medium uppercase tracking-wide flex items-center gap-2">
                    <div className="w-1 h-3 bg-green-400/60 rounded-full"></div>
                    Overall Feedback
                  </div>
                  <div className="space-y-4 text-sm">
                    <div className="bg-green-500/5 rounded-lg p-3 border border-green-500/10">
                      <div className="text-xs text-green-300/80 mb-1.5 font-medium">Organization & Flow</div>
                      <p className="text-white/85 leading-relaxed text-xs">{feedback.content.organization_flow.overall_feedback}</p>
                    </div>
                    <div className="bg-green-500/5 rounded-lg p-3 border border-green-500/10">
                      <div className="text-xs text-green-300/80 mb-1.5 font-medium">Persuasiveness & Impact</div>
                      <p className="text-white/85 leading-relaxed text-xs">{feedback.content.persuasiveness_impact.overall_feedback}</p>
                    </div>
                    <div className="bg-green-500/5 rounded-lg p-3 border border-green-500/10">
                      <div className="text-xs text-green-300/80 mb-1.5 font-medium">Clarity of Message</div>
                      <p className="text-white/85 leading-relaxed text-xs">{feedback.content.clarity_of_message.overall_feedback}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>


            {/* Generate Ideal Speech Button */}
            <div className="rounded-xl bg-gradient-to-r from-purple-500/10 to-blue-500/10 backdrop-blur-xl border border-purple-500/20 p-5">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-light mb-1 text-white/95">Generate Ideal Speech</h2>
                  <p className="text-white/60 font-light text-sm">
                    Create an improved version of your speech in your own voice
                  </p>
                </div>
                <button
                  onClick={handleGenerateIdealSpeech}
                  disabled={isGeneratingSpeech}
                  className="px-6 py-2.5 rounded-xl bg-white hover:bg-white/90 text-black transition-all duration-300 font-medium cursor-pointer shadow-lg hover:shadow-xl hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 text-sm flex items-center gap-2"
                >
                  {isGeneratingSpeech ? (
                    <>
                      <div className="relative w-4 h-4">
                        <div className="absolute inset-0 border-2 border-black/20 rounded-full"></div>
                        <div className="absolute inset-0 border-2 border-transparent border-t-black rounded-full animate-spin"></div>
                      </div>
                      <span>Generating...</span>
                    </>
                  ) : (
                    'Generate'
                  )}
                </button>
              </div>
              
              {fileSizeError && (
                <div className="mt-4 pt-4 border-t border-white/10">
                  <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                      <svg className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                      </svg>
                      <div className="flex-1">
                        <h3 className="text-red-300 font-medium mb-1">File Size Error</h3>
                        <p className="text-red-200/90 text-sm whitespace-pre-line leading-relaxed">{fileSizeError}</p>
                      </div>
                      <button
                        onClick={() => setFileSizeError(null)}
                        className="text-red-400 hover:text-red-300 transition-colors"
                      >
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              )}
              
              {isGeneratingSpeech && (
                <div className="mt-4 pt-4 border-t border-white/10">
                  <div className="flex items-center gap-3 text-white/60 text-sm">
                    <div className="relative w-5 h-5">
                      <div className="absolute inset-0 border-2 border-white/20 rounded-full"></div>
                      <div className="absolute inset-0 border-2 border-transparent border-t-white/60 rounded-full animate-spin"></div>
                    </div>
                    <span>Processing video, transcribing audio, and generating improved speech...</span>
                  </div>
                </div>
              )}
              
              {idealSpeechData && (
                <div className="mt-4 pt-4 border-t border-white/10 space-y-4">
                  {/* Audio Player */}
                  <div>
                    <h3 className="text-sm text-white/70 mb-2 font-medium">Generated Audio</h3>
                    <audio controls src={idealSpeechData.audioUrl} className="w-full" />
                  </div>
                  
                  {/* Original Transcription */}
                  <div>
                    <h3 className="text-sm text-white/70 mb-2 font-medium">Original Transcription</h3>
                    <div className="bg-black/20 rounded-lg p-3 border border-white/5">
                      <p className="text-white/80 leading-relaxed text-sm whitespace-pre-wrap">
                        {idealSpeechData.originalTranscription}
                      </p>
                    </div>
                  </div>
                  
                  {/* Improved Speech */}
                  <div>
                    <h3 className="text-sm text-green-300/70 mb-2 font-medium">Improved Speech</h3>
                    <div className="bg-green-500/10 rounded-lg p-3 border border-green-500/20">
                      <p className="text-white/90 leading-relaxed text-sm whitespace-pre-wrap">
                        {idealSpeechData.improvedSpeech}
                      </p>
                    </div>
                  </div>
                  
                  {/* Summary */}
                  {idealSpeechData.summary && (
                    <div>
                      <h3 className="text-sm text-white/70 mb-2 font-medium">Summary</h3>
                      <div className="bg-black/20 rounded-lg p-3 border border-white/5">
                        <p className="text-white/80 leading-relaxed text-sm">
                          {idealSpeechData.summary}
                        </p>
                      </div>
                    </div>
                  )}
                  
                  {/* Key Changes */}
                  {idealSpeechData.keyChanges && idealSpeechData.keyChanges.length > 0 && (
                    <div>
                      <h3 className="text-sm text-purple-300/70 mb-2 font-medium">Key Changes</h3>
                      <div className="space-y-2">
                        {idealSpeechData.keyChanges.map((change, idx) => (
                          <div key={idx} className="bg-purple-500/10 rounded-lg p-3 border border-purple-500/20">
                            <div className="text-xs text-purple-300/70 mb-1 font-medium">Change</div>
                            <p className="text-white/90 text-sm mb-2">{change.change}</p>
                            <div className="text-xs text-purple-300/70 mb-1 font-medium">Reason</div>
                            <p className="text-white/80 text-sm">{change.reason}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Suggestions */}
                  {idealSpeechData.suggestions && idealSpeechData.suggestions.length > 0 && (
                    <div>
                      <h3 className="text-sm text-blue-300/70 mb-2 font-medium">Suggestions</h3>
                      <ul className="space-y-1">
                        {idealSpeechData.suggestions.map((suggestion, idx) => (
                          <li key={idx} className="text-white/80 text-sm flex items-start gap-2">
                            <span className="text-blue-400 mt-1">•</span>
                            <span>{suggestion}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Chat Tab */}
        {activeTab === 'chat' && (
          <div className="rounded-xl bg-white/5 backdrop-blur-xl border border-white/10 p-5 flex flex-col" style={{ height: '600px' }}>
            <h2 className="text-lg font-light mb-4 text-white/95">Interactive Feedback Chat</h2>
            
            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto space-y-4 mb-4">
              {isInitializingChat ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <div className="relative w-12 h-12 mx-auto mb-4">
                      <div className="absolute inset-0 border-3 border-white/10 rounded-full"></div>
                      <div className="absolute inset-0 border-3 border-transparent border-t-white rounded-full animate-spin"></div>
                    </div>
                    <p className="text-white/60 text-sm">Initializing chat...</p>
                  </div>
                </div>
              ) : (
                <>
                  {chatMessages.length === 0 ? (
                    <div className="flex items-center justify-center h-full">
                      <p className="text-white/40 text-sm">Chat will be ready shortly...</p>
                    </div>
                  ) : (
                    chatMessages.map((msg, idx) => (
                      <div
                        key={idx}
                        className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`max-w-[80%] rounded-xl p-3 ${
                            msg.role === 'user'
                              ? 'bg-white text-black'
                              : 'bg-white/10 text-white border border-white/20'
                          }`}
                        >
                          {msg.role === 'assistant' ? (
                            <div className="text-sm leading-relaxed">
                              <ReactMarkdown
                                components={{
                                  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                                  strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
                                  em: ({ children }) => <em className="italic">{children}</em>,
                                  ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
                                  ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
                                  li: ({ children }) => <li className="ml-2">{children}</li>,
                                  h1: ({ children }) => <h1 className="text-lg font-semibold mb-2 mt-3 first:mt-0">{children}</h1>,
                                  h2: ({ children }) => <h2 className="text-base font-semibold mb-2 mt-3 first:mt-0">{children}</h2>,
                                  h3: ({ children }) => <h3 className="text-sm font-semibold mb-1 mt-2 first:mt-0">{children}</h3>,
                                  code: ({ children }) => <code className="bg-black/30 px-1.5 py-0.5 rounded text-xs font-mono">{children}</code>,
                                  pre: ({ children }) => <pre className="bg-black/30 p-2 rounded mb-2 overflow-x-auto">{children}</pre>,
                                  blockquote: ({ children }) => <blockquote className="border-l-2 border-white/30 pl-3 italic my-2">{children}</blockquote>,
                                  hr: () => <hr className="border-white/20 my-3" />,
                                }}
                              >
                                {msg.content}
                              </ReactMarkdown>
                            </div>
                          ) : (
                            <p className="text-sm leading-relaxed">{msg.content}</p>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                  {isSendingChat && (
                    <div className="flex justify-start">
                      <div className="bg-white/10 text-white border border-white/20 rounded-xl p-3">
                        <div className="flex gap-1">
                          <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                          <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                          <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </>
              )}
            </div>

            {/* Suggested Prompts */}
            {conversationId && chatMessages.length > 0 && chatInput.trim() === '' && (
              <div className="mb-4 space-y-2">
                <p className="text-xs text-white/50 font-medium mb-2">Suggested questions:</p>
                <div className="flex flex-wrap gap-2">
                  {[
                    "What are my main strengths?",
                    "How can I improve my eye contact?",
                    "What filler words should I reduce?",
                    "How is my pacing and delivery?",
                    "What are the top 3 things to work on?",
                  ].map((prompt, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setChatInput(prompt);
                        // Auto-send after a brief delay
                        setTimeout(() => {
                          if (conversationId && !isSendingChat) {
                            const userMessage = prompt;
                            setChatInput('');
                            setIsSendingChat(true);
                            setChatMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
                            
                            sendChatMessage(conversationId, userMessage)
                              .then((response) => {
                                setChatMessages((prev) => [...prev, { role: 'assistant', content: response.assistant_reply }]);
                              })
                              .catch((err) => {
                                setChatMessages((prev) => [...prev, {
                                  role: 'assistant',
                                  content: 'Sorry, I encountered an error. Please try again.',
                                }]);
                              })
                              .finally(() => {
                                setIsSendingChat(false);
                              });
                          }
                        }, 100);
                      }}
                      className="px-3 py-1.5 text-xs rounded-lg bg-white/5 hover:bg-white/10 text-white border border-white/10 hover:border-white/20 transition-all duration-300 cursor-pointer backdrop-blur-sm"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Chat Input */}
            <div className="flex gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendChatMessage();
                  }
                }}
                placeholder="Ask about your feedback..."
                className="flex-1 px-4 py-2.5 bg-white/5 backdrop-blur-xl border border-white/10 rounded-xl text-white placeholder-white/30 focus:outline-none focus:border-white/30 focus:bg-white/10 transition-all duration-300"
                disabled={!conversationId || isSendingChat}
              />
              <button
                onClick={handleSendChatMessage}
                disabled={!conversationId || isSendingChat || !chatInput.trim()}
                className="px-6 py-2.5 rounded-xl bg-white hover:bg-white/90 text-black transition-all duration-300 font-medium cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Send
              </button>
            </div>
          </div>
        )}

        {/* Back Button */}
        <div className="text-center pt-4">
          <button
            onClick={() => router.push('/')}
            className="px-6 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-white border border-white/10 hover:border-white/20 transition-all duration-300 font-medium cursor-pointer backdrop-blur-sm hover:scale-105 active:scale-95 text-sm"
          >
            Back to Upload
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AnalysisPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen relative text-white flex items-center justify-center p-6 overflow-hidden">
        <div className="fixed inset-0 static-gradient"></div>
        <div className="relative z-10 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
          <p className="text-white/60">Loading...</p>
        </div>
      </div>
    }>
      <AnalysisContent />
    </Suspense>
  );
}
