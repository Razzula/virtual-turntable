interface IMusicPlayer {
    togglePlay(): void;
    play(): void;
    pause(): void;
    nextTrack(): void;
    previousTrack(): void;
}

type Constructor<T> = new (...args: any[]) => T;

export abstract class MusicPlayer implements IMusicPlayer {
    private static instances: Map<Constructor<MusicPlayer>, MusicPlayer> = new Map();

    static getExistingInstance<T extends MusicPlayer>(): T {
        if (MusicPlayer.instances.size === 0) {
            throw new Error('No instance of this class exists yet');
        }
        return Array.from(MusicPlayer.instances.values())[0] as T;
    }

    static getInstance<T extends MusicPlayer>(this: Constructor<T>, ...args: ConstructorParameters<Constructor<T>>): T {
        if (!MusicPlayer.instances.has(this)) {
            const instance = new this(...args);
            MusicPlayer.instances.set(this, instance);
        }
        return MusicPlayer.instances.get(this) as T;
    }

    protected constructor() {
        // prevent direct instantiation
    }

    abstract togglePlay(): void;
    abstract play(): void;
    abstract pause(): void;
    abstract nextTrack(): void;
    abstract previousTrack(): void;
}

export default MusicPlayer;
