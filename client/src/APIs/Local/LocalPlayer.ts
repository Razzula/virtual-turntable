import { PlaybackState } from '../../types/Music';
import MusicPlayer from '../IMusicPlayer';

export class LocalPlayer extends MusicPlayer {
    private audio: HTMLAudioElement;
    private noiseAudio: HTMLAudioElement;
    private tracks: string[] = [
        'Baba Yetu',
        'Baba Yetu',
    ];
    private currentIndex: number = 0;
    private handlePlayerStateChange;
    private deviceSeed: number;

    constructor(handlePlayerStateChange: (state: PlaybackState) => void) {
        super();
        console.log('Creating Local Player instance');

        this.handlePlayerStateChange = handlePlayerStateChange;
        this.deviceSeed = this.getDeviceSeed();

        this.audio = new Audio();
        this.noiseAudio = new Audio('/virtual-turntable/vinyl.mp3');
        this.noiseAudio.loop = true;

        this.loadTrack(this.currentIndex);
        this.startNoiseFluctuation();
    }

    private getDeviceSeed(): number {
        const storedSeed = localStorage.getItem('deviceSeed');
        if (storedSeed) {
            return parseFloat(storedSeed);
        }
        const seed = this.hashString(navigator.userAgent);
        console.log(seed);
        localStorage.setItem('deviceSeed', seed.toString());
        return seed;
    }

    private hashString(str: string): number {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            hash = str.charCodeAt(i) + ((hash << 5) - hash);
        }
        return hash;
    }

    private startNoiseFluctuation() {
        setInterval(() => {
            const amplitude = 0.15; // oscillates volume between 0 and 0.3
            const frequency = 0.2; // cycles per second (adjust for gradual change)
            const seedOffset = this.deviceSeed % (2 * Math.PI);
            const t = Date.now() / 1000;
            const targetVolume = amplitude + amplitude * Math.sin(t * frequency + seedOffset);
            this.noiseAudio.volume = targetVolume;
        }, 100);
    }

    private loadTrack(index: number) {
        if (this.tracks[index]) {
            this.audio.src = `/virtual-turntable/server/track/${this.tracks[index]}`;
            this.updatePlayerState();
        }
    }

    private updatePlayerState() {
        fetch(`/virtual-turntable/server/track/meta/${this.tracks[this.currentIndex]}`)
            .then((response) => response.text())
            .then((text) => {
                const meta = JSON.parse(text);
                console.log(meta)
                const state: PlaybackState = {
                    paused: this.audio.paused,
                    track_window: {
                        current_track: meta,
                    }
                };
                this.handlePlayerStateChange(state);
            })
            .catch((err) => console.error('Error fetching metadata', err)
        );
    }

    public play() {
        this.audio.play();
        this.noiseAudio.play();
        this.updatePlayerState();
    }

    public pause() {
        this.audio.pause();
        this.noiseAudio.pause();
        this.updatePlayerState();
    }

    public togglePlay() {
        (this.audio.paused) ? this.play() : this.pause();
    }

    public nextTrack() {
        this.currentIndex = (this.currentIndex + 1) % this.tracks.length;
        this.loadTrack(this.currentIndex);
        this.play();
    }

    public previousTrack() {
        this.currentIndex = (this.currentIndex - 1 + this.tracks.length) % this.tracks.length;
        this.loadTrack(this.currentIndex);
        this.play();
    }

    public setVolume(volume: number) {
        this.audio.volume = volume / 100;
    }
}

export default LocalPlayer;
