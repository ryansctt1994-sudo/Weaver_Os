#ifndef WEAVER_ACTIVATION_V1_H
#define WEAVER_ACTIVATION_V1_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Weaver Activation Runtime ABI v1.
 *
 * This function owns capability only. Authority must be verified before entry.
 * Request and response bodies are UTF-8 JSON using weaver-activation-contract-1.
 * Return 0 on success. Any non-zero return is a fail-closed backend failure.
 */
int weaver_activate_v1(
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
