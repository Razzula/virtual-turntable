export type PlaybackState = {
    paused: boolean;
    track_window: {
        current_track: Track;
    };
};

export type Track = {
    name: string;
    album: Album;
    artists?: {
        name: string;
    }[];
};

export type Album = {
    id?: string;
    album_type?: string;
    artists?: {
        name: string;
    }[];
    images?: {
        url: string;
        height: number;
        width: number;
    }[];
    label?: string;
    name: string;
    release_date?: string;
    external_urls?: { spotify: string };
    uri: string;
};

export type User = {
    id: string,
    display_name: string;
    images: [{
        url: string;
        height: number;
        width: number;
    }],
    product: string;
    type: string;
    external_urls: { spotify: string };
};
