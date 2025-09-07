 

import React, { useState } from 'react';

const FollowupQuestionsPopup = ({ 
  sessionId, 
  questions = [], 
  onClose, 
  onSubmit,
  isOpen = true 
}) => {
  const [answers, setAnswers] = useState(Array(questions.length).fill(''));
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleAnswerChange = (index, value) => {
    const newAnswers = [...answers];
    newAnswers[index] = value;
    setAnswers(newAnswers);
  };

  const handleNext = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
    }
  };

  const handlePrevious = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1);
    }
  };

  const handleSubmit = async () => {
    const allAnswered = answers.every(answer => answer.trim());
    if (!allAnswered) {
      alert('Please answer all questions before submitting.');
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit(answers);
      onClose();
    } catch (error) {
      console.error('Error submitting answers:', error);
      alert('Failed to submit answers. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const progress = questions.length > 0 ? ((currentQuestionIndex + 1) / questions.length) * 100 : 0;
  const answeredCount = answers.filter(answer => answer.trim()).length;

  if (!isOpen || questions.length === 0) {
    return null;
  }

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        padding: '32px',
        width: '90%',
        maxWidth: '600px',
        maxHeight: '80vh',
        overflow: 'auto'
      }}>
        {/* Header */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          marginBottom: '24px'
        }}>
          <h2 style={{ 
            margin: 0, 
            fontSize: '24px',
            fontWeight: 'bold',
            color: '#333'
          }}>
            Follow-up Questions
          </h2>
          {/* <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '24px',
              cursor: 'pointer',
              color: '#666'
            }}
          >
            ×
          </button> */}
        </div>

        {/* Progress Bar */}
        <div style={{
          backgroundColor: '#e0e0e0',
          borderRadius: '10px',
          height: '8px',
          marginBottom: '16px'
        }}>
          <div
            style={{
              backgroundColor: '#4CAF50',
              height: '100%',
              borderRadius: '10px',
              width: `${progress}%`,
              transition: 'width 0.3s ease'
            }}
          />
        </div>

        <div style={{ 
          textAlign: 'center',
          marginBottom: '24px',
          fontSize: '14px',
          color: '#666'
        }}>
          Question {currentQuestionIndex + 1} of {questions.length} ({answeredCount} answered)
        </div>

        {/* Current Question */}
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{
            margin: '0 0 16px 0',
            fontSize: '18px',
            color: '#333'
          }}>
            {questions[currentQuestionIndex]}
          </h3>
          
          <textarea
            value={answers[currentQuestionIndex]}
            onChange={(e) => handleAnswerChange(currentQuestionIndex, e.target.value)}
            placeholder="Type your answer here..."
            rows={6}
            style={{
              width: '100%',
              padding: '12px',
              border: '1px solid #ccc',
              borderRadius: '4px',
              fontSize: '16px',
              resize: 'vertical',
              boxSizing: 'border-box'
            }}
          />
        </div>

        {/* Navigation */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <button
            onClick={handlePrevious}
            disabled={currentQuestionIndex === 0}
            style={{
              padding: '10px 20px',
              backgroundColor: currentQuestionIndex === 0 ? '#f5f5f5' : '#fff',
              color: currentQuestionIndex === 0 ? '#999' : '#333',
              border: '1px solid #ccc',
              borderRadius: '4px',
              cursor: currentQuestionIndex === 0 ? 'not-allowed' : 'pointer'
            }}
          >
            Previous
          </button>

          {currentQuestionIndex === questions.length - 1 ? (
            <button
              onClick={handleSubmit}
              disabled={isSubmitting}
              style={{
                padding: '10px 24px',
                backgroundColor: isSubmitting ? '#ccc' : '#4CAF50',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: isSubmitting ? 'not-allowed' : 'pointer',
                fontSize: '16px'
              }}
            >
              {isSubmitting ? 'Submitting...' : 'Submit All Answers'}
            </button>
          ) : (
            <button
              onClick={handleNext}
              style={{
                padding: '10px 20px',
                backgroundColor: '#2196F3',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Next
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

// Follow-up Redirect Screen Component
const FollowupRedirectScreen = ({ 
  userId, 
  tempWorkUpdateId, 
  onStartFollowup
}) => {
  const [isStarting, setIsStarting] = useState(false);

  const handleStartFollowup = async () => {
    setIsStarting(true);
    try {
      await onStartFollowup();
    } catch (error) {
      console.error('Error starting follow-up:', error);
      alert('Failed to start follow-up session. Please try again.');
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        padding: '40px',
        width: '50%',
        maxWidth: '500px',
        textAlign: 'center'
      }}>
        {/* Success Icon */}
        {/* <div style={{
          width: '60px',
          height: '60px',
          backgroundColor: '#2196F3',
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 24px auto',
          fontSize: '40px',
          color: 'white'
        }}>
          
        </div> */}

        

        <p style={{
          color: '#666',
          fontSize: '16px',
          lineHeight: '1.5',
          margin: '0 0 32px 0'
        }}>
          Please complete the required follow-up to submit your work update.
        </p>

        <button
          onClick={handleStartFollowup}
          disabled={isStarting}
          style={{
            padding: '12px 32px',
            backgroundColor: isStarting ? '#ccc' : '#2196F3',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: isStarting ? 'not-allowed' : 'pointer',
            fontSize: '16px',
            fontWeight: 'bold'
          }}
        >
          {isStarting ? 'Starting...' : "Let's Go"}
        </button>
      </div>
    </div>
  );
};

// Main Work Update System Component
const WorkUpdateSystem = () => {
  const [userId, setUserId] = useState('');
  const [workStatus, setWorkStatus] = useState('working'); // 'working', 'work from home', or 'onLeave'
  const [description, setDescription] = useState('');
  const [challengesFaced, setChallengesFaced] = useState('');
  const [plansForTomorrow, setPlansForTomorrow] = useState('');
  
  // State for follow-up flow
  const [showFollowupRedirect, setShowFollowupRedirect] = useState(false);
  const [showFollowupQuestions, setShowFollowupQuestions] = useState(false);
  const [tempWorkUpdateId, setTempWorkUpdateId] = useState(null); // Changed to temp ID
  const [followupData, setFollowupData] = useState(null);

  const handleSubmitWorkUpdate = async () => {
    // Validation
    if (!userId.trim()) {
      alert('Please enter your User ID');
      return;
    }

    // If working or work from home, require description. If on leave, description is optional
    if ((workStatus === 'working' || workStatus === 'work from home') && !description.trim()) {
      alert('Please enter your work description');
      return;
    }

    try {
      // Build payload based on work status
      let workUpdateData;
      
      if (workStatus === 'onLeave') {
        // On leave submission - minimal data
        workUpdateData = {
          "userId": userId.trim(),
          "work_status": "on_leave",
          "description": description.trim() || "On Leave",
          "challenges": "",
          "plans": ""
        };
      } else if (workStatus === 'work from home') {
        // Work from home submission - treat as working
        workUpdateData = {
          "userId": userId.trim(),
          "work_status": "work_from_home",
          "description": description.trim(),
          "challenges": challengesFaced.trim() || "",
          "plans": plansForTomorrow.trim() || ""
        };
      } else {
        // Working submission - full data
        workUpdateData = {
          "userId": userId.trim(),
          "work_status": "working",
          "description": description.trim(),
          "challenges": challengesFaced.trim() || "",
          "plans": plansForTomorrow.trim() || ""
        };
      }

      console.log('Submitting work update:', workUpdateData);

      // STEP 1: Save work update only
      const response = await fetch('http://localhost:8000/api/work-updates', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(workUpdateData)
      });

      console.log('Response status:', response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Raw error response:', errorText);
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
      }

      const result = await response.json();
      console.log('Work update result:', result);

      if (workStatus === 'onLeave') {
        // On leave - work update saved permanently, no follow-up needed
        alert('Your leave status has been submitted successfully!');
        resetForm();
      } else if (workStatus === 'working' || workStatus === 'work from home') {
        // Working or work from home - work update saved to temp, need follow-up to finalize
        setTempWorkUpdateId(result.tempWorkUpdateId);
        setShowFollowupRedirect(true);
      }

    } catch (error) {
      console.error('Error submitting work update:', error);
      alert('Failed to submit work update: ' + error.message);
    }
  };

  const handleStartFollowup = async () => {
    try {
      console.log('Starting follow-up session...');
      
      // STEP 2: Start follow-up session (using temp work update ID)
      const response = await fetch(`http://localhost:8000/api/followups/start?temp_work_update_id=${tempWorkUpdateId}&user_id=${userId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('Follow-up session started:', result);

      // Set follow-up data and show questions popup
      setFollowupData({
        sessionId: result.sessionId,
        questions: result.questions
      });

      // Hide redirect screen and show questions popup
      setShowFollowupRedirect(false);
      setShowFollowupQuestions(true);

    } catch (error) {
      console.error('Error starting follow-up:', error);
      throw new Error('Failed to start follow-up session: ' + error.message);
    }
  };

  const handleFollowupSubmit = async (answers) => {
    try {
      console.log('Submitting followup answers:', answers);
      
      // Call your FastAPI backend to complete the follow-up session
      const response = await fetch(`http://localhost:8000/api/followup/${followupData.sessionId}/complete`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          answers: answers
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('Follow-up completed:', result);
      
      alert('Follow-up questions completed successfully!');
      
      // Reset form and close popups
      resetForm();
      setShowFollowupQuestions(false);
      
    } catch (error) {
      console.error('Error submitting followup:', error);
      throw new Error('Failed to submit follow-up answers: ' + error.message);
    }
  };

  const resetForm = () => {
    setUserId('');
    setDescription('');
    setChallengesFaced('');
    setPlansForTomorrow('');
    setWorkStatus('working');
    setTempWorkUpdateId(null); // Reset temp ID
    setFollowupData(null);
  };

  const handleCloseFollowupRedirect = () => {
    setShowFollowupRedirect(false);
    resetForm();
  };

  const handleCloseFollowupQuestions = () => {
    setShowFollowupQuestions(false);
    resetForm();
  };

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: '#f5f5f5',
      padding: '40px 20px'
    }}>
      <div style={{
        maxWidth: '600px',
        margin: '0 auto',
        backgroundColor: 'white',
        padding: '40px',
        borderRadius: '8px',
        boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
      }}>
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <h1 style={{
            fontSize: '36px',
            fontWeight: 'bold',
            color: '#4A90E2',
            margin: '0 0 8px 0'
          }}>
            Work Update System
          </h1>
          <p style={{
            color: '#666',
            fontSize: '16px',
            margin: 0
          }}>
            Submit your daily work update and answer follow-up questions
          </p>
        </div>

        {/* User ID */}
        <div style={{ marginBottom: '24px' }}>
          <label style={{
            display: 'block',
            fontWeight: 'bold',
            marginBottom: '8px',
            color: '#333'
          }}>
            User ID *
          </label>
          <input
            type="text"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="Enter your user ID"
            style={{
              width: '100%',
              padding: '12px',
              border: '1px solid #ddd',
              borderRadius: '4px',
              fontSize: '16px',
              boxSizing: 'border-box'
            }}
          />
        </div>

        {/* Work Status Radio Buttons */}
        <div style={{ marginBottom: '24px' }}>
          <label style={{
            display: 'block',
            fontWeight: 'bold',
            marginBottom: '12px',
            color: '#333'
          }}>
            Status *
          </label>
          <div style={{
            display: 'flex',
            gap: '20px',
            marginBottom: '8px'
          }}>
            <label style={{
              display: 'flex',
              alignItems: 'center',
              cursor: 'pointer',
              padding: '12px 16px',
              border: '2px solid',
              borderColor: workStatus === 'working' ? '#4A90E2' : '#ddd',
              borderRadius: '8px',
              backgroundColor: workStatus === 'working' ? '#f0f8ff' : 'white',
              flex: 1,
              textAlign: 'center'
            }}>
              <input
                type="radio"
                value="working"
                checked={workStatus === 'working'}
                onChange={(e) => setWorkStatus(e.target.value)}
                style={{ marginRight: '8px' }}
              />
              <span style={{ fontWeight: workStatus === 'working' ? 'bold' : 'normal' }}>
                Working
              </span>
            </label>

            <label style={{
              display: 'flex',
              alignItems: 'center',
              cursor: 'pointer',
              padding: '12px 16px',
              border: '2px solid',
              borderColor: workStatus === 'work from home' ? '#4A90E2' : '#ddd',
              borderRadius: '8px',
              backgroundColor: workStatus === 'work from home' ? '#f0f8ff' : 'white',
              flex: 1,
              textAlign: 'center'
            }}>
              <input
                type="radio"
                value="work from home"
                checked={workStatus === 'work from home'}
                onChange={(e) => setWorkStatus(e.target.value)}
                style={{ marginRight: '8px' }}
              />
              <span style={{ fontWeight: workStatus === 'work from home' ? 'bold' : 'normal' }}>
                Work From Home
              </span>
            </label>

            <label style={{
              display: 'flex',
              alignItems: 'center',
              cursor: 'pointer',
              padding: '12px 16px',
              border: '2px solid',
              borderColor: workStatus === 'onLeave' ? '#FF9800' : '#ddd',
              borderRadius: '8px',
              backgroundColor: workStatus === 'onLeave' ? '#fff8e1' : 'white',
              flex: 1,
              textAlign: 'center'
            }}>
              <input
                type="radio"
                value="onLeave"
                checked={workStatus === 'onLeave'}
                onChange={(e) => setWorkStatus(e.target.value)}
                style={{ marginRight: '8px' }}
              />
              <span style={{ fontWeight: workStatus === 'onLeave' ? 'bold' : 'normal' }}>
                On Leave
              </span>
            </label>
          </div>
        </div>

        {/* Work Description - Only show when working */}
        {(workStatus === 'working' || workStatus === 'work from home') && (
          <div style={{ marginBottom: '24px' }}>
            <label style={{
              display: 'block',
              fontWeight: 'bold',
              marginBottom: '8px',
              color: '#333'
            }}>
              Work Description *
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What did you accomplish today? Be specific..."
              rows={4}
              style={{
                width: '100%',
                padding: '12px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                fontSize: '16px',
                resize: 'vertical',
                boxSizing: 'border-box'
              }}
            />
          </div>
        )}

        {/* Show additional fields only when working */}
        {(workStatus === 'working' || workStatus === 'work from home') && (
          <>
            {/* Challenges Faced - Optional */}
            <div style={{ marginBottom: '24px' }}>
              <label style={{
                display: 'block',
                fontWeight: 'bold',
                marginBottom: '8px',
                color: '#333'
              }}>
                Challenges Faced
              </label>
              <textarea
                value={challengesFaced}
                onChange={(e) => setChallengesFaced(e.target.value)}
                placeholder="Any challenges or difficulties you encountered..."
                rows={3}
                style={{
                  width: '100%',
                  padding: '12px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  fontSize: '16px',
                  resize: 'vertical',
                  boxSizing: 'border-box'
                }}
              />
            </div>

            {/* Plans for Tomorrow - Optional */}
            <div style={{ marginBottom: '32px' }}>
              <label style={{
                display: 'block',
                fontWeight: 'bold',
                marginBottom: '8px',
                color: '#333'
              }}>
                Plans for Tomorrow
              </label>
              <textarea
                value={plansForTomorrow}
                onChange={(e) => setPlansForTomorrow(e.target.value)}
                placeholder="What will you focus on tomorrow..."
                rows={3}
                style={{
                  width: '100%',
                  padding: '12px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  fontSize: '16px',
                  resize: 'vertical',
                  boxSizing: 'border-box'
                }}
              />
            </div>
          </>
        )}

        {/* Submit Button */}
        <button
          onClick={handleSubmitWorkUpdate}
          style={{
            width: '100%',
            padding: '16px',
            backgroundColor: workStatus === 'onLeave' ? '#FF9800' : '#4A90E2',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            fontSize: '18px',
            fontWeight: 'bold',
            cursor: 'pointer'
          }}
        >
          {workStatus === 'onLeave' ? 'Submit Leave Status' : 'Submit Work Update'}
        </button>

        {/* Status indicator */}
        {workStatus === 'onLeave' && (
          <div style={{
            marginTop: '16px',
            padding: '12px',
            backgroundColor: '#fff3cd',
            border: '1px solid #ffeaa7',
            borderRadius: '4px',
            color: '#856404',
            fontSize: '14px',
            textAlign: 'center'
          }}>
            ℹ️ No further details needed for leave days
          </div>
        )}
      </div>

      {/* Follow-up Redirect Screen */}
      {showFollowupRedirect && (
        <FollowupRedirectScreen
          userId={userId}
          tempWorkUpdateId={tempWorkUpdateId}
          onStartFollowup={handleStartFollowup}
        />
      )}

      {/* Follow-up Questions Popup */}
      {showFollowupQuestions && followupData && (
        <FollowupQuestionsPopup
          sessionId={followupData.sessionId}
          questions={followupData.questions}
          isOpen={showFollowupQuestions}
          onClose={handleCloseFollowupQuestions}
          onSubmit={handleFollowupSubmit}
        />
      )}
    </div>
  );
};

export default WorkUpdateSystem;




