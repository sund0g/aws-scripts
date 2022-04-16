#!/usr/bin/bash

brew upgrade aws-rotate-iam-keys

printf "\n\n"

profiles=(
  <your_profile>
)

for profile in "${profiles[@]}"; do
   aws-rotate-iam-keys --profile $profile
   printf "\n\n"
done

exit 42
