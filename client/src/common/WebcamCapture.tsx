import React, { useRef, useEffect, useState } from 'react';

type WebcamCaptureProps = {
    handlePhoto: (photo: string) => void;
};

const WebcamCapture: React.FC<WebcamCaptureProps> = ({ handlePhoto }) => {
    const videoRef = useRef<HTMLVideoElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [photo, setPhoto] = useState<string | null>(null);

    useEffect(() => {
        if (photo === null) {
            const startCamera = async () => {
                if (navigator.mediaDevices?.getUserMedia) {
                    try {
                        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
                        if (videoRef.current) {
                            videoRef.current.srcObject = stream;
                            videoRef.current.play();
                        }
                    } catch (err) {
                        console.error('Error accessing webcam:', err);
                    }
                } else {
                    console.error('getUserMedia not supported');
                }
            };
            startCamera();
        }
    }, [photo]);

    const takePhoto = (): void => {
        if (videoRef.current && canvasRef.current) {
            const videoWidth = videoRef.current.videoWidth;
            const videoHeight = videoRef.current.videoHeight;
            const size = Math.min(videoWidth, videoHeight);
            const startX = (videoWidth - size) / 2;
            const startY = (videoHeight - size) / 2;
            canvasRef.current.width = size;
            canvasRef.current.height = size;
            const ctx = canvasRef.current.getContext('2d');
            if (ctx) {
                ctx.drawImage(videoRef.current, startX, startY, size, size, 0, 0, size, size);
                setPhoto(canvasRef.current.toDataURL('image/png'));
            }
        }
    };

    const clearPhoto = (): void => setPhoto(null);

    const confirmPhoto = (): void => {
        if (photo) {
            handlePhoto(photo);
        }
    };

    const uploadImage = (): void => {
        fileInputRef.current?.click();
    };

    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>): void => {
        const file = e.target.files?.[0];
        if (file) {
            const reader = new FileReader();
            reader.onloadend = () => {
                setPhoto(reader.result as string);
            };
            reader.readAsDataURL(file);
        }
    };

    const renderCapturedPhoto = () => (
        <div>
            <img
                src={photo!}
                alt="Captured"
                style={{
                    width: '100%',
                    objectFit: 'cover',
                    aspectRatio: '1 / 1',
                }}
            />
            <button onClick={clearPhoto}>Clear Photo</button>
            <button onClick={confirmPhoto}>Confirm Photo</button>
        </div>
    );

    const renderVideoStream = () => (
        <div>
            <video
                ref={videoRef}
                style={{
                    width: '100%',
                    objectFit: 'cover',
                    aspectRatio: '1 / 1',
                }}
            />
            <button onClick={takePhoto}>Take Photo</button>
            <button onClick={uploadImage}>Upload Image</button>
            <canvas ref={canvasRef} style={{ display: 'none' }} />
            <input
                type="file"
                accept="image/*"
                ref={fileInputRef}
                style={{ display: 'none' }}
                onChange={handleFileUpload}
            />
        </div>
    );

    return photo ? renderCapturedPhoto() : renderVideoStream();
};

export default WebcamCapture;
