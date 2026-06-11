import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Music4, Upload, Sparkles, Play, SkipForward,
  Wand2, Settings2, ChevronRight, Check,
  Mic2, Calendar, Sliders, Eye, Download, RefreshCw,
  Clock, Zap, Heart, Star, TrendingUp,
  Disc3, Radio, Headphones, AudioWaveform
} from 'lucide-react';
import './SandalwoodStudio.css';

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
};

const cardVariants = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: { opacity: 1, scale: 1 },
  hover: { scale: 1.02, transition: { duration: 0.2 } }
};

// Singer profile images (using gradient placeholders)
const SINGER_COLORS = {
  'dr_rajkumar': ['#FFD700', '#FFA500'],
  'spb': ['#4169E1', '#00CED1'],
  'rajesh_krishnan': ['#FF6347', '#FF4500'],
  'chitra': ['#DA70D6', '#FF69B4'],
  'shreya_ghoshal': ['#FF1493', '#FF69B4'],
  'yesudas': ['#2E8B57', '#3CB371'],
  'sonu_nigam': ['#6A5ACD', '#7B68EE'],
  'unknown': ['#708090', '#778899'],
};

const ERA_COLORS = {
  '1960s_classical': '#D4AF37',
  '1970s_melodic': '#CD853F',
  '1980s_disco': '#FF6B6B',
  '1990s_hamsalekha': '#4ECDC4',
  '2000s_modern': '#45B7D1',
  '2010s_contemporary': '#96CEB4',
  '2020s_indie': '#DDA0DD',
};

// Step indicator component
const StepIndicator = ({ steps, currentStep }) => (
  <div className="step-indicator">
    {steps.map((step, index) => (
      <div key={index} className="step-item">
        <motion.div
          className={`step-circle ${index < currentStep ? 'completed' : ''} ${index === currentStep ? 'active' : ''}`}
          animate={{
            scale: index === currentStep ? 1.1 : 1,
            backgroundColor: index <= currentStep ? 'var(--accent-primary)' : 'var(--bg-tertiary)'
          }}
        >
          {index < currentStep ? <Check size={14} /> : index + 1}
        </motion.div>
        <span className="step-label">{step}</span>
        {index < steps.length - 1 && (
          <div className={`step-line ${index < currentStep ? 'completed' : ''}`} />
        )}
      </div>
    ))}
  </div>
);

// Singer card component
const SingerCard = ({ singer, isDetected, confidence, onSelect }) => {
  const colors = SINGER_COLORS[singer.id] || SINGER_COLORS['unknown'];

  return (
    <motion.div
      className={`singer-card ${isDetected ? 'detected' : ''}`}
      variants={cardVariants}
      whileHover="hover"
      onClick={() => onSelect(singer)}
    >
      <div
        className="singer-avatar"
        style={{ background: `linear-gradient(135deg, ${colors[0]}, ${colors[1]})` }}
      >
        <Mic2 size={24} />
      </div>
      <div className="singer-info">
        <h4>{singer.name}</h4>
        <span className="singer-era">{singer.era}</span>
        {isDetected && (
          <motion.div
            className="confidence-badge"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
          >
            {Math.round(confidence * 100)}% match
          </motion.div>
        )}
      </div>
      {isDetected && (
        <motion.div
          className="detected-indicator"
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
        >
          <Sparkles size={16} />
        </motion.div>
      )}
    </motion.div>
  );
};

// Era timeline component
const EraTimeline = ({ eras, detectedEra }) => (
  <div className="era-timeline">
    {eras.map((era, index) => (
      <motion.div
        key={era.id}
        className={`era-item ${detectedEra?.id === era.id ? 'detected' : ''}`}
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: index * 0.1 }}
      >
        <div
          className="era-marker"
          style={{ backgroundColor: ERA_COLORS[era.id] }}
        />
        <div className="era-content">
          <span className="era-years">{era.years[0]}-{era.years[1]}</span>
          <h5>{era.name}</h5>
          <span className="era-style">{era.style}</span>
          {detectedEra?.id === era.id && (
            <motion.span
              className="era-detected-badge"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
            >
              Detected
            </motion.span>
          )}
        </div>
      </motion.div>
    ))}
  </div>
);

// Track card component
const TrackCard = ({ track, onAnalyze, isAnalyzing }) => (
  <motion.div
    className="track-card"
    layout
    initial={{ opacity: 0, scale: 0.9 }}
    animate={{ opacity: 1, scale: 1 }}
    exit={{ opacity: 0, scale: 0.9 }}
  >
    <div className="track-icon">
      <Music4 size={20} />
    </div>
    <div className="track-info">
      <h4>{track.name}</h4>
      <div className="track-meta">
        {track.analysis ? (
          <>
            <span className="meta-item">
              <Zap size={12} /> {track.analysis.bpm?.toFixed(0) || '?'} BPM
            </span>
            <span className="meta-item">
              <Music4 size={12} /> {track.analysis.key_str || '?'}
            </span>
            <span className="meta-item">
              <TrendingUp size={12} /> {(track.analysis.energy * 100).toFixed(0)}%
            </span>
          </>
        ) : (
          <span className="meta-item text-muted">{track.size_mb} MB</span>
        )}
      </div>
      {track.singer && (
        <div className="track-singer">
          <Mic2 size={12} />
          <span>{track.singer.name}</span>
        </div>
      )}
      {track.era && (
        <div className="track-era" style={{ color: ERA_COLORS[track.era.id] }}>
          <Calendar size={12} />
          <span>{track.era.name}</span>
        </div>
      )}
    </div>
    <div className="track-actions">
      {!track.analysis && (
        <motion.button
          className="btn btn-sm btn-primary"
          onClick={() => onAnalyze(track)}
          disabled={isAnalyzing}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          {isAnalyzing ? <RefreshCw size={14} className="spin" /> : <Wand2 size={14} />}
          Analyze
        </motion.button>
      )}
      {track.analysis && (
        <span className="badge badge-success">
          <Check size={12} /> Ready
        </span>
      )}
    </div>
  </motion.div>
);

// Cue point editor component
const CuePointEditor = ({ track, cuePoints, onUpdate }) => {
  const cueTypes = [
    { id: 'mix_in', label: 'Mix In', color: '#10b981', icon: Play },
    { id: 'mix_out', label: 'Mix Out', color: '#f59e0b', icon: SkipForward },
    { id: 'drop', label: 'Drop', color: '#ef4444', icon: Zap },
    { id: 'loop_start', label: 'Loop', color: '#6366f1', icon: RefreshCw },
  ];

  return (
    <div className="cue-editor">
      <div className="cue-track-info">
        <Music4 size={16} />
        <span>{track.name}</span>
      </div>
      <div className="cue-points-grid">
        {cueTypes.map(cue => {
          const point = cuePoints?.[cue.id];
          const Icon = cue.icon;
          return (
            <motion.div
              key={cue.id}
              className={`cue-point-item ${point ? 'has-value' : ''}`}
              style={{ '--cue-color': cue.color }}
              whileHover={{ scale: 1.02 }}
            >
              <div className="cue-header">
                <Icon size={14} style={{ color: cue.color }} />
                <span>{cue.label}</span>
              </div>
              <div className="cue-value">
                {point ? (
                  <span>{point.time?.toFixed(1)}s</span>
                ) : (
                  <span className="text-muted">Auto</span>
                )}
              </div>
              <input
                type="range"
                min="0"
                max={track.analysis?.duration || 300}
                step="0.5"
                value={point?.time || 0}
                onChange={(e) => onUpdate(track.name, cue.id, parseFloat(e.target.value))}
                className="cue-slider"
              />
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};

// Transition preview component
const TransitionPreview = ({ track1, track2, onPreview, isLoading }) => (
  <motion.div
    className="transition-preview-card"
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
  >
    <div className="preview-header">
      <Eye size={18} />
      <h4>Transition Preview</h4>
    </div>
    <div className="preview-tracks">
      <div className="preview-track">
        <span className="track-label">From</span>
        <span className="track-name">{track1?.name || 'Select track'}</span>
      </div>
      <div className="preview-arrow">
        <ChevronRight size={20} />
      </div>
      <div className="preview-track">
        <span className="track-label">To</span>
        <span className="track-name">{track2?.name || 'Select track'}</span>
      </div>
    </div>
    <div className="preview-options">
      <select className="preview-type-select">
        <option value="crossfade">Crossfade</option>
        <option value="bass_swap">Bass Swap</option>
        <option value="filter_sweep">Filter Sweep</option>
        <option value="echo_out">Echo Out</option>
      </select>
      <input
        type="number"
        placeholder="Duration (s)"
        defaultValue={8}
        min={2}
        max={30}
        className="preview-duration-input"
      />
    </div>
    <motion.button
      className="btn btn-primary w-full"
      onClick={onPreview}
      disabled={!track1 || !track2 || isLoading}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      {isLoading ? (
        <>
          <RefreshCw size={16} className="spin" />
          Generating...
        </>
      ) : (
        <>
          <Headphones size={16} />
          Preview Transition
        </>
      )}
    </motion.button>
  </motion.div>
);

// Style selector component
const StyleSelector = ({ selected, onSelect }) => {
  const styles = [
    { id: 'energetic', name: 'Energetic', icon: Zap, description: 'High energy, punchy transitions' },
    { id: 'smooth', name: 'Smooth', icon: Heart, description: 'Gentle flow, long transitions' },
    { id: 'showcase', name: 'Showcase', icon: Star, description: 'Best moments highlighted' },
  ];

  return (
    <div className="style-selector">
      {styles.map(style => (
        <motion.div
          key={style.id}
          className={`style-option ${selected === style.id ? 'selected' : ''}`}
          onClick={() => onSelect(style.id)}
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
        >
          <div className="style-icon">
            <style.icon size={24} />
          </div>
          <div className="style-info">
            <h4>{style.name}</h4>
            <p>{style.description}</p>
          </div>
          {selected === style.id && (
            <motion.div
              className="style-check"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
            >
              <Check size={16} />
            </motion.div>
          )}
        </motion.div>
      ))}
    </div>
  );
};

// Main Sandalwood Studio component
export default function SandalwoodStudio() {
  const [currentStep, setCurrentStep] = useState(0);
  const [tracks, setTracks] = useState([]);
  const [selectedTracks, setSelectedTracks] = useState([]);
  const [singerProfiles, setSingerProfiles] = useState([]);
  const [eraProfiles, setEraProfiles] = useState([]);
  const [selectedStyle, setSelectedStyle] = useState('energetic');
  const [duration, setDuration] = useState(10);
  const [isCreating, setIsCreating] = useState(false);
  const [taskId, setTaskId] = useState(null);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [customCuePoints, setCustomCuePoints] = useState({});
  const [planData, setPlanData] = useState(null);
  const [planId, setPlanId] = useState(null);
  const [groupStyles, setGroupStyles] = useState({});
  const [isPlanLoading, setIsPlanLoading] = useState(false);

  const steps = ['Select Tracks', 'Analyze', 'Review Plan', 'Configure', 'Results'];

  const getGradeLetter = (percentage) => {
    if (percentage >= 80) return 'A';
    if (percentage >= 65) return 'B';
    if (percentage >= 50) return 'C';
    if (percentage >= 35) return 'D';
    return 'F';
  };

  const fetchSongs = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/songs');
      const data = await res.json();
      setTracks(data.songs || []);
    } catch (err) {
      console.error('Failed to fetch songs:', err);
    }
  };

  const fetchProfiles = async () => {
    try {
      const [singersRes, erasRes] = await Promise.all([
        fetch('http://localhost:8000/api/singer/profiles'),
        fetch('http://localhost:8000/api/era/profiles'),
      ]);
      const singersData = await singersRes.json();
      const erasData = await erasRes.json();
      setSingerProfiles(singersData.singers || []);
      setEraProfiles(erasData.eras || []);
    } catch (err) {
      console.error('Failed to fetch profiles:', err);
    }
  };

  // Fetch available songs and profiles on mount
  useEffect(() => {
    fetchSongs();
    fetchProfiles();
  }, []);

  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files);
    const formData = new FormData();

    for (const file of files) {
      formData.append('file', file);
      try {
        await fetch('http://localhost:8000/api/songs/upload', {
          method: 'POST',
          body: formData,
        });
      } catch (err) {
        console.error('Upload failed:', err);
      }
    }

    fetchSongs();
  };

  const analyzeTrack = async (track) => {
    try {
      const res = await fetch('http://localhost:8000/api/analyze/kannada', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: track.name }),
      });
      const data = await res.json();

      // Poll for completion
      if (data.task_id) {
        pollTask(data.task_id, (result) => {
          setTracks(prev => prev.map(t =>
            t.name === track.name ? { ...t, analysis: result } : t
          ));
        });
      }
    } catch (err) {
      console.error('Analysis failed:', err);
    }
  };

  const detectSinger = async (track) => {
    try {
      const res = await fetch('http://localhost:8000/api/singer/detect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: track.name }),
      });
      const data = await res.json();

      if (data.task_id) {
        pollTask(data.task_id, (result) => {
          setTracks(prev => prev.map(t =>
            t.name === track.name ? { ...t, singer: result } : t
          ));
        });
      }
    } catch (err) {
      console.error('Singer detection failed:', err);
    }
  };

  const pollTask = async (taskId, onComplete) => {
    const poll = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/tasks/${taskId}`);
        const data = await res.json();

        if (data.status === 'completed') {
          onComplete(data.result);
        } else if (data.status === 'failed') {
          console.error('Task failed:', data.error);
        } else {
          setProgress(data.progress || 0);
          setTimeout(poll, 1000);
        }
      } catch (err) {
        console.error('Poll failed:', err);
      }
    };
    poll();
  };

  const handleCuePointUpdate = (trackName, cueType, time) => {
    setCustomCuePoints(prev => ({
      ...prev,
      [trackName]: {
        ...prev[trackName],
        [cueType]: { time, is_custom: true }
      }
    }));
  };

  const createMashup = async () => {
    setIsCreating(true);
    setProgress(0);

    try {
      const res = await fetch('http://localhost:8000/api/mashup/sandalwood', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filenames: selectedTracks.map(t => t.name),
          style: selectedStyle,
          duration: duration,
        }),
      });
      const data = await res.json();

      if (data.task_id) {
        setTaskId(data.task_id);
        pollTask(data.task_id, (result) => {
          setResult(result);
          setIsCreating(false);
          setCurrentStep(4);
        });
      }
    } catch (err) {
      console.error('Mashup creation failed:', err);
      setIsCreating(false);
    }
  };

  const createPallaviMedley = async () => {
    setIsCreating(true);
    setProgress(0);

    try {
      const res = await fetch('http://localhost:8000/api/mashup/pallavi-medley', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filenames: selectedTracks.map(t => t.name),
        }),
      });
      const data = await res.json();

      if (data.task_id) {
        setTaskId(data.task_id);
        pollTask(data.task_id, (result) => {
          setResult(result);
          setIsCreating(false);
          setCurrentStep(4);
        });
      }
    } catch (err) {
      console.error('Pallavi medley creation failed:', err);
      setIsCreating(false);
    }
  };

  const generatePlan = async () => {
    setIsPlanLoading(true);
    setProgress(0);
    try {
      const res = await fetch('http://localhost:8000/api/mashup/sandalwood/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filenames: selectedTracks.map(t => t.name),
          duration: duration,
        }),
      });
      const data = await res.json();
      if (data.task_id) {
        setTaskId(data.task_id);
        pollTask(data.task_id, (result) => {
          setPlanData(result);
          setPlanId(result.plan_id);
          const styles = {};
          (result.groups || []).forEach(g => {
            styles[g.group_id] = g.style;
          });
          setGroupStyles(styles);
          setIsPlanLoading(false);
          setCurrentStep(2);
        });
      }
    } catch (err) {
      console.error('Plan generation failed:', err);
      setIsPlanLoading(false);
    }
  };

  const createFromPlan = async () => {
    setIsCreating(true);
    setProgress(0);
    try {
      const groups = Object.entries(groupStyles).map(([gid, style]) => ({
        group_id: parseInt(gid),
        style: style,
      }));
      const res = await fetch('http://localhost:8000/api/mashup/sandalwood/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plan_id: planId,
          groups: groups,
        }),
      });
      const data = await res.json();
      if (data.task_id) {
        setTaskId(data.task_id);
        pollTask(data.task_id, (result) => {
          setResult(result);
          setIsCreating(false);
          setCurrentStep(4);
        });
      }
    } catch (err) {
      console.error('Create from plan failed:', err);
      setIsCreating(false);
    }
  };

  return (
    <div className="sandalwood-studio">
      {/* Hero Header */}
      <motion.header
        className="studio-header"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="header-content">
          <motion.div
            className="logo-section"
            whileHover={{ scale: 1.02 }}
          >
            <div className="logo-icon">
              <Disc3 size={32} />
            </div>
            <div className="logo-text">
              <h1>Sandalwood Studio</h1>
              <span className="version-badge">V2.3</span>
            </div>
          </motion.div>
          <p className="tagline">Professional Kannada Mashup Creation</p>
        </div>
        <div className="header-glow" />
      </motion.header>

      {/* Step Indicator */}
      <StepIndicator steps={steps} currentStep={currentStep} />

      {/* Main Content */}
      <motion.main
        className="studio-main"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        <AnimatePresence mode="wait">
          {/* Step 0: Select Tracks */}
          {currentStep === 0 && (
            <motion.div
              key="step-0"
              className="step-content"
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
            >
              <div className="content-grid">
                {/* Track Selection Panel */}
                <div className="panel glass-card">
                  <div className="panel-header">
                    <Music4 size={20} />
                    <h3>Select Tracks</h3>
                    <span className="badge badge-primary">{selectedTracks.length} selected</span>
                  </div>

                  <div className="upload-zone">
                    <input
                      type="file"
                      id="file-upload"
                      multiple
                      accept="audio/*"
                      onChange={handleFileUpload}
                      hidden
                    />
                    <label htmlFor="file-upload" className="upload-label">
                      <Upload size={24} />
                      <span>Drop files or click to upload</span>
                    </label>
                  </div>

                  <div className="tracks-list">
                    <AnimatePresence>
                      {tracks.map(track => (
                        <motion.div
                          key={track.name}
                          className={`track-item ${selectedTracks.includes(track) ? 'selected' : ''}`}
                          onClick={() => {
                            if (selectedTracks.includes(track)) {
                              setSelectedTracks(prev => prev.filter(t => t !== track));
                            } else {
                              setSelectedTracks(prev => [...prev, track]);
                            }
                          }}
                          layout
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: -10 }}
                          whileHover={{ backgroundColor: 'rgba(255,255,255,0.05)' }}
                        >
                          <div className="track-checkbox">
                            {selectedTracks.includes(track) && <Check size={14} />}
                          </div>
                          <div className="track-details">
                            <span className="track-name">{track.name}</span>
                            <span className="track-size">{track.size_mb} MB</span>
                          </div>
                          {track.has_analysis && (
                            <span className="badge badge-success">Analyzed</span>
                          )}
                        </motion.div>
                      ))}
                    </AnimatePresence>
                  </div>
                </div>

                {/* Singer Profiles Panel */}
                <div className="panel glass-card">
                  <div className="panel-header">
                    <Mic2 size={20} />
                    <h3>Singer Profiles</h3>
                  </div>
                  <div className="singers-grid">
                    {singerProfiles.map(singer => (
                      <SingerCard
                        key={singer.id}
                        singer={singer}
                        isDetected={false}
                        onSelect={() => {}}
                      />
                    ))}
                  </div>
                </div>
              </div>

              <div className="step-actions">
                <motion.button
                  className="btn btn-primary btn-lg"
                  onClick={() => setCurrentStep(1)}
                  disabled={selectedTracks.length < 2}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  Continue
                  <ChevronRight size={18} />
                </motion.button>
              </div>
            </motion.div>
          )}

          {/* Step 1: Analyze */}
          {currentStep === 1 && (
            <motion.div
              key="step-1"
              className="step-content"
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
            >
              <div className="content-grid">
                {/* Analysis Panel */}
                <div className="panel glass-card panel-wide">
                  <div className="panel-header">
                    <Wand2 size={20} />
                    <h3>Deep Analysis</h3>
                    <motion.button
                      className="btn btn-secondary"
                      onClick={() => selectedTracks.forEach(t => !t.analysis && analyzeTrack(t))}
                      whileHover={{ scale: 1.02 }}
                    >
                      <Wand2 size={14} />
                      Analyze All
                    </motion.button>
                  </div>

                  <div className="analysis-grid">
                    {selectedTracks.map(track => (
                      <TrackCard
                        key={track.name}
                        track={track}
                        onAnalyze={analyzeTrack}
                        isAnalyzing={false}
                      />
                    ))}
                  </div>

                  <div className="analysis-features">
                    <h4>17-Step Analysis Includes:</h4>
                    <div className="features-grid">
                      {[
                        'BPM & Beat Grid', 'Tala Detection', 'Key/Ragam', 'Vocal Regions',
                        'Pallavi/Charanam', 'Energy Curve', 'Hook Detection', 'DJ Cue Points'
                      ].map(feature => (
                        <span key={feature} className="feature-tag">
                          <Check size={12} /> {feature}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Era Detection */}
                <div className="panel glass-card">
                  <div className="panel-header">
                    <Calendar size={20} />
                    <h3>Film Era Timeline</h3>
                  </div>
                  <EraTimeline eras={eraProfiles} detectedEra={null} />
                </div>
              </div>

              <div className="step-actions">
                <button className="btn btn-secondary" onClick={() => setCurrentStep(0)}>
                  Back
                </button>
                <motion.button
                  className="btn btn-primary btn-lg"
                  onClick={generatePlan}
                  disabled={selectedTracks.some(t => !t.analysis && !t.has_analysis) || isPlanLoading}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  {isPlanLoading ? (
                    <><RefreshCw size={18} className="spin" /> Generating Plan...</>
                  ) : (
                    <>Generate Plan <ChevronRight size={18} /></>
                  )}
                </motion.button>
              </div>
            </motion.div>
          )}

          {/* Step 2: Review Plan */}
          {currentStep === 2 && planData && (
            <motion.div
              key="step-2-plan"
              className="step-content"
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
            >
              <div className="plan-review">
                {/* Matrix Summary */}
                <div className="matrix-summary glass-card">
                  <h3>Compatibility Matrix</h3>
                  <div className="matrix-stats">
                    <span className="grade-badge grade-A">A: {planData.matrix_summary?.grade_A || 0}</span>
                    <span className="grade-badge grade-B">B: {planData.matrix_summary?.grade_B || 0}</span>
                    <span className="grade-badge grade-C">C: {planData.matrix_summary?.grade_C || 0}</span>
                    <span className="grade-badge grade-D">D: {planData.matrix_summary?.grade_D || 0}</span>
                    <span className="grade-badge grade-F">F: {planData.matrix_summary?.grade_F || 0}</span>
                  </div>
                  <p className="text-muted">{planData.matrix_summary?.total_pairs || 0} pairs analyzed from {planData.total_analyzed || 0} tracks</p>
                </div>

                {/* Group Cards */}
                <div className="groups-grid">
                  {(planData.groups || []).map(group => (
                    <div key={group.group_id} className="group-card glass-card">
                      <div className="group-header">
                        <h4>{group.name}</h4>
                        <span className={`compat-badge grade-${getGradeLetter(group.avg_compatibility)}`}>
                          {group.avg_compatibility}%
                        </span>
                      </div>
                      <div className="group-tracks">
                        {(group.track_order || []).map(fn => (
                          <div key={fn} className="group-track-item">
                            <Music4 size={14} /> {fn}
                          </div>
                        ))}
                      </div>
                      <div className="group-meta">
                        <span><Clock size={14} /> ~{group.estimated_duration_minutes} min</span>
                        <span><Zap size={14} /> {group.track_count} tracks</span>
                      </div>
                      {group.warnings && group.warnings.length > 0 && (
                        <div className="group-warnings">
                          {group.warnings.map((w, i) => (
                            <span key={i} className="text-muted">⚠ {w}</span>
                          ))}
                        </div>
                      )}
                      <div className="group-style-override">
                        <label>Style:</label>
                        <select
                          value={groupStyles[group.group_id] || group.style}
                          onChange={(e) => setGroupStyles(prev => ({
                            ...prev, [group.group_id]: e.target.value
                          }))}
                        >
                          <option value="energetic">Energetic</option>
                          <option value="smooth">Smooth</option>
                          <option value="showcase">Showcase</option>
                        </select>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Excluded Tracks */}
                {planData.excluded && planData.excluded.length > 0 && (
                  <div className="excluded-panel glass-card">
                    <h4>Excluded Tracks ({planData.excluded.length})</h4>
                    {planData.excluded.map(ex => (
                      <div key={ex.filename} className="excluded-item">
                        <span>{ex.filename}</span>
                        <span className="text-muted">{ex.reason} (best: {ex.best_score}%)</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="step-actions">
                <button className="btn btn-secondary" onClick={() => setCurrentStep(1)}>
                  Back
                </button>
                <motion.button
                  className="btn btn-primary btn-lg"
                  onClick={() => setCurrentStep(3)}
                  disabled={!planData.groups || planData.groups.length === 0}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  Configure & Create <ChevronRight size={18} />
                </motion.button>
              </div>
            </motion.div>
          )}

          {/* Step 3: Configure */}
          {currentStep === 3 && (
            <motion.div
              key="step-2"
              className="step-content"
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
            >
              <div className="content-grid three-col">
                {/* Style Selection */}
                <div className="panel glass-card">
                  <div className="panel-header">
                    <Settings2 size={20} />
                    <h3>Mashup Style</h3>
                  </div>
                  <StyleSelector selected={selectedStyle} onSelect={setSelectedStyle} />

                  <div className="duration-control">
                    <label>Duration (minutes)</label>
                    <div className="duration-input-group">
                      <input
                        type="range"
                        min="5"
                        max="30"
                        value={duration}
                        onChange={(e) => setDuration(parseInt(e.target.value))}
                      />
                      <span className="duration-value">{duration} min</span>
                    </div>
                  </div>

                  <div className="medley-option">
                    <motion.button
                      className="btn btn-secondary w-full"
                      onClick={createPallaviMedley}
                      whileHover={{ scale: 1.02 }}
                    >
                      <Radio size={16} />
                      Create Pallavi Medley Instead
                    </motion.button>
                    <p className="option-description">
                      Chorus-to-chorus transitions for authentic Kannada medley style
                    </p>
                  </div>
                </div>

                {/* Cue Points */}
                <div className="panel glass-card">
                  <div className="panel-header">
                    <Sliders size={20} />
                    <h3>Custom Cue Points</h3>
                  </div>
                  <div className="cue-editors">
                    {selectedTracks.slice(0, 3).map(track => (
                      <CuePointEditor
                        key={track.name}
                        track={track}
                        cuePoints={customCuePoints[track.name]}
                        onUpdate={handleCuePointUpdate}
                      />
                    ))}
                  </div>
                </div>

                {/* Preview */}
                <div className="panel glass-card">
                  <div className="panel-header">
                    <Eye size={20} />
                    <h3>Preview</h3>
                  </div>
                  <TransitionPreview
                    track1={selectedTracks[0]}
                    track2={selectedTracks[1]}
                    onPreview={() => {}}
                    isLoading={false}
                  />
                </div>
              </div>

              <div className="step-actions">
                <button className="btn btn-secondary" onClick={() => setCurrentStep(2)}>
                  Back
                </button>
                <motion.button
                  className="btn btn-primary btn-lg create-btn"
                  onClick={planData ? createFromPlan : createMashup}
                  disabled={isCreating}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  {isCreating ? (
                    <>
                      <RefreshCw size={18} className="spin" />
                      Creating... {progress}%
                    </>
                  ) : planData ? (
                    <>
                      <Sparkles size={18} />
                      Create All Mixes ({planData.groups?.length || 0} groups)
                    </>
                  ) : (
                    <>
                      <Sparkles size={18} />
                      Create Mashup
                    </>
                  )}
                </motion.button>
              </div>
            </motion.div>
          )}

          {/* Step 4: Results */}
          {currentStep === 4 && result && (
            <motion.div
              key="step-4"
              className="step-content"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
            >
              <div className="result-panel glass-card">
                <motion.div
                  className="result-success"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", stiffness: 200 }}
                >
                  <div className="success-icon">
                    <Check size={48} />
                  </div>
                  <h2>{result.mashups ? `${result.total_created} Mashup${result.total_created !== 1 ? 's' : ''} Created!` : 'Mashup Created!'}</h2>
                  <p>Your professional Sandalwood mashup{result.mashups ? 's are' : ' is'} ready</p>
                </motion.div>

                {/* Multiple mashup results (from Plan → Create flow) */}
                {result.mashups ? (
                  <div className="result-mashups-list">
                    {result.mashups.map(mashup => (
                      <div key={mashup.group_id} className="result-mashup-item glass-card">
                        <div className="mashup-item-header">
                          <h4>{mashup.group_name}</h4>
                          <span className="badge badge-primary">{mashup.style}</span>
                        </div>
                        <p className="text-muted">{mashup.track_count} tracks</p>
                        {mashup.output_filename ? (
                          <motion.a
                            href={`http://localhost:8000/api/stream/${mashup.output_filename}`}
                            className="btn btn-primary"
                            download
                            whileHover={{ scale: 1.02 }}
                          >
                            <Download size={16} /> Download
                          </motion.a>
                        ) : (
                          <span className="text-muted">Failed: {mashup.error}</span>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  /* Single mashup result (legacy flow) */
                  <>
                    <div className="result-details">
                      <div className="result-stat">
                        <Music4 size={20} />
                        <div>
                          <span className="stat-label">Tracks</span>
                          <span className="stat-value">{result.track_count || selectedTracks.length}</span>
                        </div>
                      </div>
                      <div className="result-stat">
                        <Clock size={20} />
                        <div>
                          <span className="stat-label">Style</span>
                          <span className="stat-value">{result.style || selectedStyle}</span>
                        </div>
                      </div>
                      <div className="result-stat">
                        <AudioWaveform size={20} />
                        <div>
                          <span className="stat-label">Format</span>
                          <span className="stat-value">320kbps MP3</span>
                        </div>
                      </div>
                    </div>

                    <div className="result-actions">
                      <motion.a
                        href={`http://localhost:8000/api/stream/${result.output_filename}`}
                        className="btn btn-primary btn-lg"
                        download
                        whileHover={{ scale: 1.02 }}
                      >
                        <Download size={18} />
                        Download Mashup
                      </motion.a>
                    </div>
                  </>
                )}

                <div className="result-actions">
                  <motion.button
                    className="btn btn-secondary"
                    onClick={() => {
                      setCurrentStep(0);
                      setSelectedTracks([]);
                      setResult(null);
                      setPlanData(null);
                      setPlanId(null);
                      setGroupStyles({});
                    }}
                    whileHover={{ scale: 1.02 }}
                  >
                    <RefreshCw size={16} />
                    Create Another
                  </motion.button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.main>

      {/* Progress Overlay */}
      <AnimatePresence>
        {isCreating && (
          <motion.div
            className="progress-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div className="progress-modal glass-card">
              <div className="progress-animation">
                <motion.div
                  className="progress-disc"
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                >
                  <Disc3 size={64} />
                </motion.div>
              </div>
              <h3>Creating Your Mashup</h3>
              <p className="progress-status">
                {progress < 30 ? 'Analyzing tracks...' :
                 progress < 60 ? 'Synchronizing BPM...' :
                 progress < 80 ? 'Applying transitions...' :
                 'Finalizing output...'}
              </p>
              <div className="progress-bar">
                <motion.div
                  className="progress-bar-fill"
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                />
              </div>
              <span className="progress-percent">{progress}%</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
