#!/usr/bin/env bash
set -u
SCRIPT="$(dirname "$0")/preview-sanitize-branch.sh"

assert_eq() {
  local got="$1" expected="$2" name="$3"
  if [ "$got" = "$expected" ]; then
    echo "OK  $name"
  else
    echo "FAIL $name: got='$got' expected='$expected'"
    exit 1
  fi
}

assert_eq "$("$SCRIPT" "main")" "main" "main passes through"
assert_eq "$("$SCRIPT" "feat-a")" "feat-a" "simple slug passes"
assert_eq "$("$SCRIPT" "feature/vendor-self-service/backend")" \
  "feature-vendor-self-service-ba" "long path slashed and truncated to 30"
assert_eq "$("$SCRIPT" "Feature_X.1")" "feature-x-1" "lowercase, _ and . to -"
assert_eq "$("$SCRIPT" "-leading-dash")" "leading-dash" "leading dash trimmed"
assert_eq "$("$SCRIPT" "trailing-dash-")" "trailing-dash" "trailing dash trimmed"

echo "all sanitize tests passed"
