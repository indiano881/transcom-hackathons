import { useState, useEffect } from 'react';

const MESSAGES = [
    "Spinning up the hamsters...",
    "Convincing the cloud to cooperate...",
    "Downloading more RAM...",
    "Compiling your genius...",
    "Asking the intern where the server is...",
    "Deploying to the moon... almost...",
    "Making sure the bits are in order...",
    "Feeding the server elves...",
    "Optimizing for maximum fun...",
    "Reticulating splines...",
    "Summoning the demo gods...",
    "Polishing the pixels...",
    "Sending carrier pigeons...",
    "Warming up the servers...",
    "Converting coffee to code...",
    "Doing some magic...",
    "Counting to infinity...",
    "Dividing by zero... wait, no...",
    "Checking the gravity...",
    "Loading the loading bar...",
    "Distracting the project manager...",
    "Buying more cloud credits...",
    "Checking for typos...",
    "Hiring more hamsters...",
    "Updating the progress bar...",
    "Writing more status messages...",
    "Pretending to work...",
    "Making it look easy...",
    "Sweeping the bits under the rug...",
    "Waiting for the stars to align...",
    "Asking nicely...",
    "Trying to turn it off and on again...",
    "Making sure it works on my machine...",
];

export default function FunDeploymentStatus() {
    const [currentMessage, setCurrentMessage] = useState(MESSAGES[0]);

    useEffect(() => {
        let index = 0;
        // Fisher-Yates shuffle to randomize order on mount
        const shuffled = [...MESSAGES].sort(() => Math.random() - 0.5);
        setCurrentMessage(shuffled[0]);

        const interval = setInterval(() => {
            index = (index + 1) % shuffled.length;
            setCurrentMessage(shuffled[index]);
        }, 4000);

        return () => clearInterval(interval);
    }, []);

    return (
        <div style={{
            textAlign: 'center',
            padding: '2rem',
            backgroundColor: 'var(--gray-50)',
            borderRadius: '8px',
            margin: '1rem 0',
            border: '1px solid var(--gray-200)',
            animation: 'fadeIn 0.5s ease-in'
        }}>
            <div style={{
                fontSize: '1.2rem',
                fontWeight: '600',
                color: 'var(--primary)',
                marginBottom: '0.5rem',
                minHeight: '1.5em', // reserve space for text
                transition: 'opacity 0.3s ease-in-out'
            }}>
                {currentMessage}
            </div>
            <div style={{
                fontSize: '0.9rem',
                color: 'var(--gray-500)'
            }}>
                Hang tight, this might take a minute!
            </div>
            <style>{`
        @keyframes indeterminate {
          0% { transform:  translateX(0) scaleX(0); }
          40% { transform:  translateX(0) scaleX(0.4); }
          100% { transform:  translateX(100%) scaleX(0.5); }
        }
      `}</style>
        </div>
    );
}
