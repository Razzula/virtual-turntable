import '@testing-library/jest-dom';
import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { vi, describe, test, expect, beforeEach } from 'vitest';
import WebcamCapture from '../src/common/WebcamCapture';

if (typeof globalThis.MediaStream === 'undefined') {
    (globalThis as any).MediaStream = class MediaStream {
        constructor() { }
    };
}

describe('WebcamCapture', () => {
    const dummyDataUrl = "data:image/png;base64,dummy";

    beforeEach(() => {
        // Mock navigator.mediaDevices.getUserMedia
        if (!navigator.mediaDevices) {
            (navigator as any).mediaDevices = {};
        }
        navigator.mediaDevices.getUserMedia = vi.fn().mockResolvedValue(new MediaStream());

        // Mock FileReader to simulate reading a file as a Data URL
        vi.spyOn(window, 'FileReader').mockImplementation(() => {
            const fileReaderMock = {
                result: dummyDataUrl,
                readAsDataURL: vi.fn().mockImplementation(function (this: any, file: File) {
                    this.result = dummyDataUrl;
                    if (this.onloadend) {
                        this.onloadend();
                    }
                }),
            };
            return fileReaderMock as unknown as FileReader;
        });
    });

    test('renders video stream view when no photo is captured', () => {
        const { container } = render(<WebcamCapture handlePhoto={vi.fn()} />);
        // Expect a <video> element is present.
        expect(container.querySelector('video')).toBeInTheDocument();
        // Check for the "Take Photo" and "Upload Image" buttons.
        expect(screen.getByText('Take Photo')).toBeInTheDocument();
        expect(screen.getByText('Upload Image')).toBeInTheDocument();
    });

    test('uploads file and renders captured photo view', async () => {
        const handlePhotoMock = vi.fn();
        render(<WebcamCapture handlePhoto={handlePhotoMock} />);
        // Get the hidden file input.
        const input = document.querySelector('input[type="file"]') as HTMLInputElement;
        expect(input).toBeDefined();
        // Create a dummy file.
        const file = new File(['dummy content'], 'test.png', { type: 'image/png' });
        // Fire a change event on the file input.
        fireEvent.change(input, { target: { files: [file] } });
        // Wait for the component to render the captured photo view.
        await waitFor(() => {
            expect(screen.getByAltText('Captured')).toBeInTheDocument();
            expect(screen.getByText('Clear Photo')).toBeInTheDocument();
            expect(screen.getByText('Confirm Photo')).toBeInTheDocument();
        });
    });

    test('clears photo when "Clear Photo" button is clicked', async () => {
        const handlePhotoMock = vi.fn();
        render(<WebcamCapture handlePhoto={handlePhotoMock} />);
        // Simulate file upload.
        const input = document.querySelector('input[type="file"]') as HTMLInputElement;
        const file = new File(['dummy content'], 'test.png', { type: 'image/png' });
        fireEvent.change(input, { target: { files: [file] } });
        await waitFor(() => {
            expect(screen.getByAltText('Captured')).toBeInTheDocument();
        });
        // Click the "Clear Photo" button.
        fireEvent.click(screen.getByText('Clear Photo'));
        // After clearing, the video stream should be rendered again.
        await waitFor(() => {
            expect(document.querySelector('video')).toBeInTheDocument();
            expect(screen.getByText('Take Photo')).toBeInTheDocument();
        });
    });

    test('calls handlePhoto when "Confirm Photo" button is clicked', async () => {
        const handlePhotoMock = vi.fn();
        render(<WebcamCapture handlePhoto={handlePhotoMock} />);
        // Simulate file upload.
        const input = document.querySelector('input[type="file"]') as HTMLInputElement;
        const file = new File(['dummy content'], 'test.png', { type: 'image/png' });
        fireEvent.change(input, { target: { files: [file] } });
        await waitFor(() => {
            expect(screen.getByAltText('Captured')).toBeInTheDocument();
        });
        // Click the "Confirm Photo" button.
        fireEvent.click(screen.getByText('Confirm Photo'));
        // The handlePhoto prop should be called with the captured image data URL.
        expect(handlePhotoMock).toHaveBeenCalledWith(dummyDataUrl);
    });
});
