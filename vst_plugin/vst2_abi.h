/*
 * Minimal VST 2.4 ABI declarations.
 *
 * Steinberg no longer distributes the VST2 SDK, so this header declares only
 * the subset of the (well-documented, binary-stable) plugin interface that
 * this project needs. It is written from scratch and contains no SDK code.
 */

#ifndef VST2_ABI_H
#define VST2_ABI_H

#include <stdint.h>

#define VST_MAGIC 0x56737450 /* 'VstP' */

typedef struct AEffect AEffect;

typedef intptr_t (*audioMasterCallback)(AEffect *effect, int32_t opcode, int32_t index,
                                        intptr_t value, void *ptr, float opt);
typedef intptr_t (*AEffectDispatcherProc)(AEffect *effect, int32_t opcode, int32_t index,
                                          intptr_t value, void *ptr, float opt);
typedef void (*AEffectProcessProc)(AEffect *effect, float **inputs, float **outputs,
                                   int32_t sampleFrames);
typedef void (*AEffectProcessDoubleProc)(AEffect *effect, double **inputs, double **outputs,
                                         int32_t sampleFrames);
typedef void (*AEffectSetParameterProc)(AEffect *effect, int32_t index, float parameter);
typedef float (*AEffectGetParameterProc)(AEffect *effect, int32_t index);

struct AEffect {
    int32_t magic;
    AEffectDispatcherProc dispatcher;
    AEffectProcessProc process; /* deprecated accumulating process */
    AEffectSetParameterProc setParameter;
    AEffectGetParameterProc getParameter;
    int32_t numPrograms;
    int32_t numParams;
    int32_t numInputs;
    int32_t numOutputs;
    int32_t flags;
    intptr_t resvd1;
    intptr_t resvd2;
    int32_t initialDelay;
    int32_t realQualities;
    int32_t offQualities;
    float ioRatio;
    void *object;
    void *user;
    int32_t uniqueID;
    int32_t version;
    AEffectProcessProc processReplacing;
    AEffectProcessDoubleProc processDoubleReplacing;
    char future[56];
};

typedef struct ERect {
    int16_t top, left, bottom, right;
} ERect;

/* AEffect.flags */
enum {
    effFlagsHasEditor = 1 << 0,
    effFlagsCanReplacing = 1 << 4,
    effFlagsNoSoundInStop = 1 << 9,
};

/* Host -> plugin opcodes (dispatcher) */
enum {
    effOpen = 0,
    effClose = 1,
    effGetProgramName = 5,
    effGetParamLabel = 6,
    effGetParamDisplay = 7,
    effGetParamName = 8,
    effSetSampleRate = 10,
    effSetBlockSize = 11,
    effMainsChanged = 12,
    effEditGetRect = 13,
    effEditOpen = 14,
    effEditClose = 15,
    effEditIdle = 19,
    effGetPlugCategory = 35,
    effGetEffectName = 45,
    effGetVendorString = 47,
    effGetProductString = 48,
    effGetVendorVersion = 49,
    effCanDo = 51,
    effGetVstVersion = 58,
};

/* Plugin -> host opcodes (audioMasterCallback) */
enum {
    audioMasterVersion = 1,
};

enum {
    kPlugCategEffect = 1,
};

#endif /* VST2_ABI_H */
