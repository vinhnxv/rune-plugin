import React from 'react';

export default function SignUp() {
  return (
    <div className="relative bg-zinc-50 w-360 h-[1737px] overflow-hidden">
      <div className="flex flex-col justify-center items-center gap-12">
      <div className="flex flex-col items-center gap-2">
      <svg className="bg-[#c4c4c4] w-12 h-12 rounded-full" aria-label="Logo" role="img" width="48" height="48" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M48 24C48 37.2548 37.2548 48 24 48C10.7452 48 0 37.2548 0 24C0 10.7452 10.7452 0 24 0C37.2548 0 48 10.7452 48 24Z" fillRule="nonzero" fill="currentColor" />
    </svg>
      <h1 className="text-zinc-800 w-[617px] h-12 text-[32px] font-medium leading-normal text-center font-['Poppins']" aria-level="1" role="heading">Sign up for free to start live-streaming</h1>
    </div>
      <div className="flex flex-col gap-4">
      <div className="relative w-144.5 h-16 bg-zinc-50 border border-zinc-800 border-solid rounded-3xl overflow-hidden">
      <div className="flex flex-row justify-center items-center gap-4">
      <svg className="relative w-8 h-8" aria-label="Social media logo" role="img" width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* TODO: SVG paths for Social media logo */}
    </svg>
      <h2 className="text-zinc-800 w-[247px] h-[33px] text-2xl font-normal leading-snug font-['Avenir']" aria-level="2" role="heading">Sign up with Facebook</h2>
    </div>
    </div>
      <div className="relative w-144.5 h-16 bg-zinc-50 border border-zinc-800 border-solid rounded-3xl overflow-hidden">
      <div className="flex flex-row justify-center items-center gap-4">
      <svg className="relative w-6 h-6 overflow-hidden" aria-label="Social media logo" role="img" width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* TODO: SVG paths for Social media logo */}
    </svg>
      <h2 className="text-zinc-800 w-55.5 h-[33px] text-2xl font-normal leading-snug font-['Avenir']" aria-level="2" role="heading">Sign up with Google</h2>
    </div>
    </div>
      <div className="relative w-144.5 h-16 bg-zinc-50 border border-zinc-800 border-solid rounded-3xl overflow-hidden">
      <div className="flex flex-row justify-center items-center gap-4">
      <svg className="relative w-8 h-8" aria-label="Social media logo" role="img" width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* TODO: SVG paths for Social media logo */}
    </svg>
      <h2 className="text-zinc-800 w-53.5 h-[33px] text-2xl font-normal leading-snug font-['Avenir']" aria-level="2" role="heading">Sign up with Twitter</h2>
    </div>
    </div>
    </div>
      <div className="flex flex-row items-center gap-[23px] w-144.5">
      <div className="bg-[#666666] w-[248px] h-0.5" />
      <h2 className="text-[#666666] w-[35px] h-[33px] text-2xl font-normal leading-snug font-['Avenir']" aria-level="2" role="heading">OR</h2>
      <div className="bg-[#666666] w-[248px] h-0.5" />
    </div>
      <div className="flex flex-col justify-center items-center gap-10">
      <p className="text-zinc-800 w-[291px] h-[27px] text-lg font-medium leading-normal text-center font-['Poppins']">Sign up with your email address</p>
      <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1 w-144.5">
      <input aria-label="Text field" type="text" />
      <div className="relative w-full h-[27px]">
      <p className="text-[#666666] w-[101px] h-6 text-base font-normal leading-normal font-['Poppins']">Profile name</p>
    </div>
      <div className="relative w-full h-14 border border-[#666666] border-solid rounded-lg overflow-hidden">
      <input aria-label="Text field" type="text" />
      <div className="flex flex-row items-center">
      <input aria-label="Inputs" type="text" />
      <p className="text-[#666666] w-46.5 h-6 text-base font-normal leading-normal font-['Poppins']">Enter your profile name</p>
    </div>
    </div>
    </div>
      <div className="flex flex-col gap-1 w-144.5">
      <input aria-label="Text field" type="text" />
      <div className="relative w-full h-[27px]">
      <p className="text-[#666666] w-11 h-6 text-base font-normal leading-normal font-['Poppins']">Email</p>
    </div>
      <div className="relative w-full h-14 border border-[#666666] border-solid rounded-lg overflow-hidden">
      <input aria-label="Text field" type="text" />
      <div className="flex flex-row items-center">
      <input aria-label="Inputs" type="text" />
      <p className="text-[#666666] w-[199px] h-6 text-base font-normal leading-normal font-['Poppins']">Enter your email address</p>
    </div>
    </div>
    </div>
      <div className="flex flex-col gap-1 w-144.5">
      <input aria-label="Text field" type="text" />
      <div className="relative w-full h-[27px]">
      <p className="text-[#666666] w-[77px] h-6 text-base font-normal leading-normal font-['Poppins']">Password</p>
      <div className="relative w-[73px] h-[27px]">
      <svg className="relative w-6 h-6 overflow-hidden" aria-label="icon" role="img" width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* TODO: SVG paths for icon */}
    </svg>
      <p className="text-[#666666] w-[41px] h-[27px] text-lg font-normal leading-normal text-right font-['Poppins']">Hide</p>
    </div>
    </div>
      <div className="relative w-full h-14 border border-[#666666] border-solid rounded-lg overflow-hidden">
      <input aria-label="Text field" type="text" />
      <div className="flex flex-row items-center">
      <input aria-label="Inputs" type="text" />
      <p className="text-[#666666] w-[163px] h-6 text-base font-normal leading-normal font-['Poppins']">Enter your password</p>
    </div>
    </div>
      <p className="text-[#666666] w-[463px] h-[21px] text-sm font-normal leading-normal font-['Poppins']">Use 8 or more characters with a mix of letters, numbers & symbols</p>
    </div>
    </div>
      <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-3">
      <p className="text-neutral-900 w-62.5 h-6 text-base font-normal leading-normal font-['Poppins']">
      <span className="text-base font-normal leading-normal font-['Poppins']">What’s your gender? </span>
      <span className="text-[#666666]">(optional)</span>
    </p>
      <div className="flex flex-row gap-8">
      <button className="flex flex-row justify-center items-center gap-2 px-2" type="button">
      <svg className="relative w-4 h-4 overflow-hidden" aria-label="Radio button" role="img" width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* TODO: SVG paths for Radio button */}
    </svg>
      <p className="text-neutral-900 w-15 h-6 text-base font-normal leading-normal font-['Poppins']">Female</p>
    </button>
      <button className="flex flex-row justify-center items-center gap-2 px-2" type="button">
      <svg className="relative w-4 h-4 overflow-hidden" aria-label="Radio button" role="img" width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* TODO: SVG paths for Radio button */}
    </svg>
      <p className="text-neutral-900 w-[39px] h-6 text-base font-normal leading-normal font-['Poppins']">Male</p>
    </button>
      <button className="flex flex-row justify-center items-center gap-2 px-2" type="button">
      <svg className="relative w-4 h-4 overflow-hidden" aria-label="Radio button" role="img" width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* TODO: SVG paths for Radio button */}
    </svg>
      <p className="text-neutral-900 w-23 h-6 text-base font-normal leading-normal font-['Poppins']">Non-binary</p>
    </button>
    </div>
    </div>
      <div className="flex flex-col gap-3">
      <p className="text-neutral-900 w-53 h-6 text-base font-normal leading-normal font-['Poppins']">What’s your date of borth?</p>
      <div className="flex flex-row gap-5">
      <div className="flex flex-col gap-1 w-45">
      <input aria-label="Text field" type="text" />
      <div className="relative w-full h-[27px]">
      <p className="text-[#666666] w-[51px] h-6 text-base font-normal leading-normal font-['Poppins']">Month</p>
    </div>
      <div className="relative w-full h-14 border border-[#666666] border-solid rounded-lg overflow-hidden">
      <input aria-label="Text field" type="text" />
      <svg className="relative w-6 h-6 overflow-hidden" aria-label="Icons" role="img" width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* TODO: SVG paths for Icons */}
    </svg>
    </div>
    </div>
      <div className="flex flex-col gap-1 w-[179px]">
      <input aria-label="Text field" type="text" />
      <div className="relative w-full h-[27px]">
      <p className="text-[#666666] w-9.5 h-6 text-base font-normal leading-normal font-['Poppins']">Date</p>
    </div>
      <div className="relative w-full h-14 border border-[#666666] border-solid rounded-lg overflow-hidden">
      <input aria-label="Text field" type="text" />
      <svg className="relative w-6 h-6 overflow-hidden" aria-label="Icons" role="img" width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* TODO: SVG paths for Icons */}
    </svg>
    </div>
    </div>
      <div className="flex flex-col gap-1 w-[179px]">
      <input aria-label="Text field" type="text" />
      <div className="relative w-full h-[27px]">
      <p className="text-[#666666] w-[37px] h-6 text-base font-normal leading-normal font-['Poppins']">Year</p>
    </div>
      <div className="relative w-full h-14 border border-[#666666] border-solid rounded-lg overflow-hidden">
      <input aria-label="Text field" type="text" />
      <svg className="relative w-6 h-6 overflow-hidden" aria-label="Icons" role="img" width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* TODO: SVG paths for Icons */}
    </svg>
    </div>
    </div>
    </div>
    </div>
    </div>
      <div className="flex flex-col gap-6">
      <div className="flex flex-row gap-2 pt-2 pr-2 pb-2">
      <svg className="relative w-6 h-6 overflow-hidden" aria-label="Check box" role="img" width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* TODO: SVG paths for Check box */}
    </svg>
      <p className="text-zinc-800 w-[459px] h-12 text-base font-normal leading-normal font-['Poppins']">Share my registration data with our content providers for <br />
    marketing purposes.</p>
    </div>
      <div className="flex flex-row gap-2.5 pt-2 pr-2 pb-2">
      <p className="text-[#666666] w-146 h-6 text-base font-normal leading-normal font-['Poppins']">
      <span className="text-zinc-800">By creating an account, you agree to the </span>
      <span className="text-base underline text-neutral-900">Terms of use</span>
      <span className="text-base"> </span>
      <span className="text-zinc-800">and</span>
      <span className="text-base"> </span>
      <span className="text-base underline text-neutral-900">Privacy Policy.</span>
      <span className="text-base underline"> </span>
    </p>
    </div>
      <div className="relative w-[363px] h-17 bg-zinc-50 border border-zinc-800 border-solid rounded-xl">
      <div className="flex flex-row justify-center items-center gap-2">
      <svg className="relative w-4.5 h-4.5 overflow-hidden" aria-label="Check box" role="img" width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* TODO: SVG paths for Check box */}
    </svg>
      <p className="text-zinc-800 w-[117px] h-6 text-base font-light leading-normal text-center font-['Poppins']">I’m not a robot</p>
    </div>
      <svg className="relative w-12 h-[46px] overflow-hidden" aria-label="google_recaptcha-official 2" role="img" width="48" height="46" viewBox="0 0 48 46" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* TODO: SVG paths for google_recaptcha-official 2 */}
    </svg>
    </div>
    </div>
      <div className="flex flex-col justify-center items-center gap-4">
      <button className="relative w-144.5 h-16 bg-neutral-900 rounded-[40px] opacity-25 overflow-hidden" type="button">
      <div className="flex flex-row justify-center items-center gap-2">
      <h3 className="text-zinc-50 w-21 h-[33px] text-[22px] font-medium leading-normal text-center font-['Poppins']" aria-level="3" role="heading">Sign up</h3>
    </div>
    </button>
      <div className="flex flex-row gap-2.5 p-0.5">
      <p className="text-[#666666] w-[251px] h-6 text-base font-normal leading-normal font-['Poppins'] underline">
      <span className="text-base text-zinc-800">Already have an ccount?</span>
      <span className="text-base text-[#666666]"> </span>
      <span className="text-base underline text-neutral-900">Log in  </span>
    </p>
    </div>
    </div>
    </div>
    </div>
    </div>
  );
}
