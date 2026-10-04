#ifndef WEAVER_VOID_NATIVE_V1_H
#define WEAVER_VOID_NATIVE_V1_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Capability-only ABI. Authority must be verified before this function is called.
 * Return 0 on success. Any non-zero return is a fail-closed backend failure.
 * response_len must be set to the exact number of UTF-8 JSON bytes written.
 */
int weaver_void_activate_v1(
    const char *request_json,
    size_t request_len,
    const uint8_t *input_bytes,
    size_t input_len,
    char *response_json,
    size_t response_capacity,
    size_t *response_len
);

#ifdef __cplusplus
}
#endif

#endif
