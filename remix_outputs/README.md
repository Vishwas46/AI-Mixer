1# AI-DJ Mashup Session

This directory contains a series of AI-generated mashups created by the AI-Mixer project. The goal of this session was to analyze a collection of dance tracks and create a series of harmonically and rhythmically compatible mashups, simulating a DJ's creative process.

## The Process

1.  **Song Analysis:** Each track in the `songs` directory was analyzed to determine its BPM (Beats Per Minute) and musical key.
2.  **Curation & Pairing:** Based on the analysis, tracks were paired to ensure maximum compatibility. The primary factors for pairing were matching keys and similar BPMs.
3.  **Creative Mixing:** For each pair, the `creative_remix.py` script was used to perform the following:
    *   **Source Separation:** The vocals were isolated from one track and the instrumental from the other using Demucs.
    *   **Tempo Synchronization:** The tracks were time-stretched to match a common BPM.
    *   **Harmonic Alignment:** The pitch of the vocals was shifted to match the key of the instrumental.
    *   **Final Mixdown:** The aligned vocal and instrumental tracks were combined into a final mashup.

## The Mashups

### 1. `01_Titanium_Losing_It_Mashup.mp3`

*   **Vocals:** David Guetta - "Titanium" (123 BPM, G:min)
*   **Instrumental:** FISHER - "Losing It" (123 BPM, G:min)
*   **Notes:** A perfect match. The identical BPM and key create a seamless and powerful big-room anthem.

### 2. `02_Levels_Sandstorm_Mashup.mp3`

*   **Vocals:** Avicii - "Levels" (123 BPM, E:maj)
*   **Instrumental:** Darude - "Sandstorm" (136 BPM, E:min)
*   **Notes:** A classic major/minor key relationship. The iconic melody of "Levels" soars over the driving, timeless energy of the "Sandstorm" instrumental.

### 3. `03_Satisfaction_Adagio_Mashup.mp3`

*   **Vocals:** Benny Benassi - "Satisfaction" (129 BPM, A#:min)
*   **Instrumental:** Tiësto - "Adagio For Strings" (144 BPM, A#:min)
*   **Notes:** A dramatic and intense pairing. The relentless electro vocals of "Satisfaction" are layered over the epic, emotional trance soundscape of "Adagio For Strings".

