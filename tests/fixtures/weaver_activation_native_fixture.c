#include <stddef.h>
#include <stdint.h>
#include <string.h>

int weaver_activate_v1(
    const char *request_json,
    size_t request_len,
    const uint8_t *input_bytes,
    size_t input_len,
    char *response_json,
    size_t response_capacity,
    size_t *response_len
) {
    const char *response =
        "{\"backend_id\":\"weaver-native-c\","
        "\"checkpoint_sha256\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\","
        "\"contract_version\":\"weaver-activation-contract-1\","
        "\"model_id\":\"m1\","
        "\"output_sha256\":\"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc\","
        "\"primary_metric\":0.75,"
        "\"request_id\":\"req-native\","
        "\"retention_metric\":0.999}";
    size_t len = strlen(response);
    (void)request_json;
    (void)request_len;
    (void)input_bytes;
    (void)input_len;
    if (response_len == NULL || response_json == NULL || response_capacity < len) {
        return 2;
    }
    memcpy(response_json, response, len);
    *response_len = len;
    return 0;
}
